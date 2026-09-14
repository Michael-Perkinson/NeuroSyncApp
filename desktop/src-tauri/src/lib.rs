use serde::Serialize;
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    io::{BufRead, BufReader, Read, Write},
    path::PathBuf,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{atomic::{AtomicU64, Ordering}, Mutex},
    thread,
    time::{Duration, Instant},
};
use tauri::{AppHandle, Emitter, Manager, State};

const PROTOCOL_VERSION: u64 = 1;
const MAX_FRAME_BYTES: usize = 4 * 1024 * 1024;

#[derive(Debug, Serialize)]
struct HostError {
    code: &'static str,
    user_text: &'static str,
    recovery: &'static str,
    details: Value,
}

impl HostError {
    fn new(code: &'static str, user_text: &'static str, recovery: &'static str) -> Self {
        Self { code, user_text, recovery, details: json!({}) }
    }
}

#[derive(Serialize, Clone)]
struct LogEntry {
    level: &'static str,
    message: String,
}

#[derive(Serialize)]
struct NativeGrant {
    grant_id: String,
    kind: String,
    display_name: String,
    path: String,
}

struct Sidecar {
    child: Child,
    stdin: ChildStdin,
    stdout: ChildStdout,
}

impl Sidecar {
    fn spawn(app: &AppHandle) -> Result<Self, HostError> {
        let mut command = sidecar_command()?;
        command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        let mut child = command.spawn().map_err(|_| HostError::new(
            "sidecar_start_failed", "The scientific sidecar could not be started.", "restart_sidecar"
        ))?;
        let stdin = child.stdin.take().ok_or_else(|| HostError::new(
            "sidecar_pipe_failed", "The sidecar input pipe is unavailable.", "restart_sidecar"
        ))?;
        let stdout = child.stdout.take().ok_or_else(|| HostError::new(
            "sidecar_pipe_failed", "The sidecar output pipe is unavailable.", "restart_sidecar"
        ))?;
        if let Some(stderr) = child.stderr.take() {
            let handle = app.clone();
            thread::spawn(move || {
                for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                    let bounded: String = line.chars().take(4096).collect();
                    let _ = handle.emit("sidecar-log", LogEntry { level: "info", message: bounded });
                }
            });
        }
        Ok(Self { child, stdin, stdout })
    }

    fn request(&mut self, request: &Value) -> Result<Value, HostError> {
        let payload = serde_json::to_vec(request).map_err(|_| HostError::new(
            "request_encode_failed", "The request could not be encoded.", "retry"
        ))?;
        if payload.len() > MAX_FRAME_BYTES {
            return Err(HostError::new("frame_too_large", "The request exceeds the 4 MiB protocol limit.", "change_input"));
        }
        self.stdin.write_all(&(payload.len() as u32).to_be_bytes()).and_then(|_| self.stdin.write_all(&payload)).and_then(|_| self.stdin.flush())
            .map_err(|_| HostError::new("sidecar_write_failed", "The sidecar connection was lost.", "restart_sidecar"))?;
        let mut header = [0_u8; 4];
        self.stdout.read_exact(&mut header).map_err(|_| HostError::new(
            "sidecar_read_failed", "The sidecar did not return a complete response.", "restart_sidecar"
        ))?;
        let length = u32::from_be_bytes(header) as usize;
        if length == 0 || length > MAX_FRAME_BYTES {
            return Err(HostError::new("invalid_response_frame", "The sidecar returned an invalid frame.", "restart_sidecar"));
        }
        let mut bytes = vec![0_u8; length];
        self.stdout.read_exact(&mut bytes).map_err(|_| HostError::new(
            "sidecar_read_failed", "The sidecar response was incomplete.", "restart_sidecar"
        ))?;
        serde_json::from_slice(&bytes).map_err(|_| HostError::new(
            "invalid_response_json", "The sidecar returned invalid protocol data.", "restart_sidecar"
        ))
    }

    fn stop(mut self) {
        let _ = self.request(&json!({
            "protocol_version": PROTOCOL_VERSION, "id": "host-shutdown",
            "method": "sidecar.shutdown", "params": {}
        }));
        let deadline = Instant::now() + Duration::from_secs(2);
        while Instant::now() < deadline {
            if matches!(self.child.try_wait(), Ok(Some(_))) { return; }
            thread::sleep(Duration::from_millis(25));
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn sidecar_command() -> Result<Command, HostError> {
    if let Some(executable) = std::env::var_os("NEUROSYNC_SIDECAR_EXECUTABLE") {
        return Ok(Command::new(executable));
    }
    if cfg!(debug_assertions) {
        let sidecar_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../sidecar");
        let python = std::env::var_os("NEUROSYNC_SIDECAR_PYTHON").or_else(|| {
            let repository_root = sidecar_dir.parent()?.parent()?;
            let virtualenv_python = if cfg!(windows) {
                repository_root.join(".venv/Scripts/python.exe")
            } else {
                repository_root.join(".venv/bin/python3")
            };
            virtualenv_python.is_file().then(|| virtualenv_python.into_os_string())
        }).unwrap_or_else(|| {
            if cfg!(windows) { "python".into() } else { "python3".into() }
        });
        let mut command = Command::new(python);
        command.arg("-m").arg("neurosync_sidecar").current_dir(sidecar_dir);
        return Ok(command);
    }
    let directory = std::env::current_exe().ok().and_then(|path| path.parent().map(PathBuf::from))
        .ok_or_else(|| HostError::new("sidecar_not_found", "The bundled sidecar location is unavailable.", "none"))?;
    let name = if cfg!(windows) { "neurosync-sidecar.exe" } else { "neurosync-sidecar" };
    Ok(Command::new(directory.join(name)))
}

struct AppState {
    sidecar: Mutex<Option<Sidecar>>,
    grants: Mutex<HashMap<String, PathBuf>>,
    next_grant: AtomicU64,
    app: AppHandle,
}

#[tauri::command]
fn start_sidecar(state: State<'_, AppState>) -> Result<Value, HostError> {
    let mut slot = state.sidecar.lock().map_err(|_| HostError::new("host_state_failed", "Host state is unavailable.", "restart_sidecar"))?;
    if slot.is_none() { *slot = Some(Sidecar::spawn(&state.app)?); }
    let response = slot.as_mut().unwrap().request(&json!({
        "protocol_version": PROTOCOL_VERSION, "id": "host-negotiate", "method": "protocol.negotiate",
        "params": {"supported_versions": [PROTOCOL_VERSION], "client": {"name": "tauri-host", "version": "0.1.0"}}
    }))?;
    response.get("result").cloned().ok_or_else(|| HostError::new(
        "protocol_negotiation_failed", "The sidecar protocol is incompatible with this host.", "none"
    ))
}

#[tauri::command]
fn proxy_sidecar_request(request: Value, state: State<'_, AppState>) -> Result<Value, HostError> {
    let mut slot = state.sidecar.lock().map_err(|_| HostError::new("host_state_failed", "Host state is unavailable.", "restart_sidecar"))?;
    slot.as_mut().ok_or_else(|| HostError::new("sidecar_not_running", "The scientific sidecar is not running.", "restart_sidecar"))?.request(&request)
}

#[tauri::command]
fn shutdown_sidecar(state: State<'_, AppState>) -> Result<(), HostError> {
    let sidecar = state.sidecar.lock().map_err(|_| HostError::new("host_state_failed", "Host state is unavailable.", "restart_sidecar"))?.take();
    if let Some(sidecar) = sidecar { sidecar.stop(); }
    Ok(())
}

#[tauri::command]
async fn select_native_grant(kind: String, state: State<'_, AppState>) -> Result<Option<NativeGrant>, HostError> {
    let path = match kind.as_str() {
        "file" => rfd::AsyncFileDialog::new().pick_file().await.map(|value| value.path().to_path_buf()),
        "folder" => rfd::AsyncFileDialog::new().pick_folder().await.map(|value| value.path().to_path_buf()),
        _ => return Err(HostError::new("invalid_grant_kind", "The requested grant type is invalid.", "change_input")),
    };
    let Some(path) = path else { return Ok(None); };
    let sequence = state.next_grant.fetch_add(1, Ordering::Relaxed);
    let grant_id = format!("grant-{sequence}");
    let display_name = path.file_name().and_then(|value| value.to_str()).unwrap_or("Selected location").to_string();
    let path_string = path.to_string_lossy().to_string();
    state.grants.lock().map_err(|_| HostError::new("host_state_failed", "Host state is unavailable.", "retry"))?.insert(grant_id.clone(), path);
    Ok(Some(NativeGrant { grant_id, kind, display_name, path: path_string }))
}

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            app.manage(AppState { sidecar: Mutex::new(None), grants: Mutex::new(HashMap::new()), next_grant: AtomicU64::new(1), app: app.handle().clone() });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![start_sidecar, proxy_sidecar_request, shutdown_sidecar, select_native_grant])
        .build(tauri::generate_context!())
        .expect("Tauri host setup failed")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit) {
                if let Some(state) = app.try_state::<AppState>() {
                    if let Ok(mut slot) = state.sidecar.lock() {
                        if let Some(sidecar) = slot.take() { sidecar.stop(); }
                    }
                }
            }
        });
}
