import csv
import pstats
import cProfile

from src.app_dashboard import AppDashboard


def on_closing():
    """Handle the closing of the application."""
    # profiler.disable()
    # profile_to_csv(profiler, 'output.csv')
    app.quit()
    app.destroy()

# # Uncomment the following code to profile the application as this is only needed for measuring the performance of the application during development.
# def profile_to_csv(profile, csv_file_path):
#     stats = pstats.Stats(profile)
#     with open(csv_file_path, 'w', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow(['ncalls', 'tottime', 'percall_tot', 'cumtime', 'percall_cum', 'filename:lineno(function)'])
#         for stat in stats.stats.items():
#             func_name = pstats.func_std_string(stat[0])
#             ncalls = stat[1][0]
#             tottime = stat[1][2]
#             cumtime = stat[1][3]
#             if ncalls != 0:
#                 percall_tot = tottime / ncalls
#                 percall_cum = cumtime / ncalls
#             else:
#                 percall_tot = percall_cum = 0
#             writer.writerow([ncalls, tottime, percall_tot, cumtime, percall_cum, func_name])


# profiler = cProfile.Profile()
# profiler.enable()

if __name__ == "__main__":
    app = AppDashboard()
    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()
