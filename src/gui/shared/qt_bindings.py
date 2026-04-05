from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit

T = TypeVar("T")


class ObservableValue(Generic[T]):
    def __init__(self, value: T | None = None) -> None:
        self._value = value
        self._callbacks: list[Callable[..., None]] = []

    def get(self) -> T | None:
        return self._value

    def set(self, value: T | None) -> None:
        if self._value == value:
            return
        self._value = value
        for callback in list(self._callbacks):
            callback()

    def trace_add(self, _mode: str, callback: Callable[..., None]) -> None:
        self._callbacks.append(lambda: callback())

    def trace(self, _mode: str, callback: Callable[..., None]) -> None:
        self.trace_add(_mode, callback)


class LineEditControl(QLineEdit):
    def __init__(
        self,
        value: ObservableValue[str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.value = value
        if self.value is not None:
            initial_value = self.value.get() or ""
            if initial_value:
                self.setText(initial_value)
            self.textChanged.connect(self.value.set)
            self.value.trace_add("write", self._sync_from_value)

    def _sync_from_value(self) -> None:
        if self.value is None:
            return
        next_value = self.value.get() or ""
        if self.text() != next_value:
            self.setText(next_value)

    def get(self) -> str:
        return self.text()

    def set(self, value: str) -> None:
        self.setText(value)

    def config(self, **kwargs) -> None:
        self.configure(**kwargs)

    def configure(self, **kwargs) -> None:
        state = kwargs.get("state")
        if state is not None:
            self.setEnabled(state not in {"disabled", False})

    def bind(self, event_name: str, callback: Callable[..., None]) -> None:
        if event_name == "<KeyRelease>":
            self.textChanged.connect(lambda *_args: callback(None))


class ComboMenuAdapter:
    def __init__(self, combo_box: "ComboBoxControl") -> None:
        self.combo_box = combo_box
        self._commands: dict[str, Callable[[], None]] = {}

    def delete(self, _start=0, _end=None) -> None:
        self._commands.clear()
        self.combo_box.blockSignals(True)
        self.combo_box.clear()
        self.combo_box.blockSignals(False)

    def add_command(self, label: str, command: Callable[[], None]) -> None:
        self._commands[label] = command
        self.combo_box.addItem(label)

    def trigger(self, label: str) -> None:
        callback = self._commands.get(label)
        if callback is not None:
            callback()


class ComboBoxControl(QComboBox):
    def __init__(
        self,
        value: ObservableValue[str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.value = value
        self.menu = ComboMenuAdapter(self)
        if self.value is not None:
            initial_value = self.value.get() or ""
            if initial_value:
                self.setCurrentText(initial_value)
            self.currentTextChanged.connect(self.value.set)
            self.value.trace_add("write", self._sync_from_value)
        self.activated.connect(self._trigger_menu_command)

    def _sync_from_value(self) -> None:
        if self.value is None:
            return
        next_value = self.value.get() or ""
        if self.currentText() != next_value:
            self.setCurrentText(next_value)

    def get(self) -> str:
        return self.currentText()

    def set(self, value: str) -> None:
        self.setCurrentText(value)

    def set_options(self, values: list[str]) -> None:
        current_text = self.currentText()
        self.blockSignals(True)
        self.clear()
        self.menu._commands.clear()
        self.addItems(values)
        if current_text in values:
            self.setCurrentText(current_text)
        elif values:
            self.setCurrentIndex(0)
        self.blockSignals(False)

    def bind(self, event_name: str, callback: Callable[..., None]) -> None:
        if event_name == "<<ComboboxSelected>>":
            self.currentIndexChanged.connect(lambda *_args: callback(None))

    def _trigger_menu_command(self) -> None:
        self.menu.trigger(self.currentText())

    def config(self, **kwargs) -> None:
        self.configure(**kwargs)

    def configure(self, **kwargs) -> None:
        state = kwargs.get("state")
        if state is not None:
            self.setEnabled(state not in {"disabled", False})

    def __setitem__(self, key: str, value) -> None:
        if key == "values":
            self.set_options(list(value))
            return
        if key == "state":
            self.configure(state=value)

    def __getitem__(self, key: str):
        if key == "menu":
            return self.menu
        if key == "values":
            return [self.itemText(index) for index in range(self.count())]
        if key == "state":
            return "normal" if self.isEnabled() else "disabled"
        raise KeyError(key)


class CheckBoxControl(QCheckBox):
    def __init__(
        self,
        text: str = "",
        value: ObservableValue[bool] | None = None,
        parent=None,
    ) -> None:
        super().__init__(text, parent)
        self.value = value
        if self.value is not None:
            self.setChecked(bool(self.value.get()))
            self.checkStateChanged.connect(self._update_value)
            self.value.trace_add("write", self._sync_from_value)

    def _update_value(self, state: int) -> None:
        if self.value is not None:
            self.value.set(state == Qt.Checked)

    def _sync_from_value(self) -> None:
        if self.value is not None:
            self.setChecked(bool(self.value.get()))

    def get(self) -> bool:
        return self.isChecked()

    def set(self, value: bool) -> None:
        self.setChecked(bool(value))

    def select(self) -> None:
        self.setChecked(True)

    def deselect(self) -> None:
        self.setChecked(False)

    def config(self, **kwargs) -> None:
        self.configure(**kwargs)

    def configure(self, **kwargs) -> None:
        state = kwargs.get("state")
        if state is not None:
            self.setEnabled(state not in {"disabled", False})
