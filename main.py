import os
import sys
import pygame
import time
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget, QTableView, QHBoxLayout, QVBoxLayout, QHeaderView,
                               QComboBox, QTextBrowser, QLineEdit, QRadioButton, QLabel, QPushButton, QMessageBox)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtCore import Qt, QTimer, QElapsedTimer
from Puzzle import generate_scramble, calculate_wca_average, calculate_wca_ao100, calculate_session_mean
from Times import (init_db, format_solve_time, Solve, insert_solve_data, fetch_tab_data, clear_tab_data, fetch_data_by_id,
                   check_solve_time, get_solve_list, delete_data_by_id, fetch_single_best, store_average_best, update_average_best,
                   fetch_average_best, clear_average_data, plus_two_solve, dnf_solve)


def get_asset_path(relative_path):
    #Get the absolute path to a sound file. Added for the making of .exe file (deployment)
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class SpeedCubeTimer(QMainWindow):
    def __init__(self):
        super().__init__()
        #Puzzle and Session tabs
        self.puzzle_tab = QComboBox()
        self.session_tab = QComboBox()

        self.time_limit_button = QRadioButton("Include time limit")
        self.time_limit_input = QLineEdit()
        self.time_limit_label = QLabel("Enter a time limit in seconds (int/float)")

        self.scramble_label = QLabel()
        #Session best records
        self.best_records_model = QStandardItemModel()
        self.best_records_view = QTableView()
        self.best_records_view.setModel(self.best_records_model)
        self.delete_session_button = QPushButton("X")

        self.session_stats_button = QPushButton("Solve:\nMean: ")
        #Session solves
        self.solve_list_model = QStandardItemModel()
        self.solve_list_view = QTableView()
        self.solve_list_view.setModel(self.solve_list_model)

        self.time_label = QLabel("0.00")

        #Solve Timer
        self.solve_timer = QTimer()
        self.solve_elapsed = QElapsedTimer()
        self.current_raw_ms = 0
        #Inspection Timer
        self.inspection_timer = QTimer()
        self.inspection_elapsed = QElapsedTimer()
        self.inspection_hold_timer = QTimer()
        self.inspection_hold_timer.setSingleShot(True)
        self.inspection_limit = 17000
        self.inspection_is_held = False

        self.has_inspection_penalty = False

        #Sound for fun
        pygame.mixer.init()
        try:
            good_path = get_asset_path("goodboy.wav")
            fail_path = get_asset_path("fahh.wav")

            self.succeeded_audio = pygame.mixer.Sound(good_path)
            self.failed_audio = pygame.mixer.Sound(fail_path)
            self.audio_loaded = True
        except Exception:
            self.audio_loaded = False

        self.set_up_layouts()
        self.set_up_styles()
        self.perform()

    #Sets up the layouts
    def set_up_layouts(self):
        main_widget = QWidget()
        main_vbox_layout = QVBoxLayout()

        hbox_layout1 = QHBoxLayout()
        hbox_layout1.addWidget(self.puzzle_tab)
        hbox_layout1.addWidget(self.time_limit_button)
        hbox_layout1.addWidget(self.time_limit_input)
        hbox_layout1.addWidget(self.time_limit_label)
        hbox_layout1.addStretch(1)

        main_vbox_layout.addLayout(hbox_layout1)
        main_vbox_layout.addWidget(self.scramble_label)

        hbox_layout2 = QHBoxLayout()

        hbox_layout3 = QHBoxLayout()
        hbox_layout3.addWidget(self.session_tab)
        hbox_layout3.addWidget(self.delete_session_button)

        secondary_vbox_layout = QVBoxLayout()
        secondary_vbox_layout.addLayout(hbox_layout3)
        secondary_vbox_layout.addWidget(self.best_records_view)
        secondary_vbox_layout.addWidget(self.session_stats_button)
        secondary_vbox_layout.addWidget(self.solve_list_view)

        hbox_layout2.addLayout(secondary_vbox_layout)
        hbox_layout2.addWidget(self.time_label, stretch=1)

        main_vbox_layout.addLayout(hbox_layout2)

        main_widget.setLayout(main_vbox_layout)
        self.setCentralWidget(main_widget)

    #Sets up the styles
    def set_up_styles(self):
        self.setWindowTitle("Speedcube Timer")
        self.setWindowIcon(QIcon("speedcube_icon.png"))

        self.puzzle_tab.addItems(["2x2", "3x3", "4x4", "5x5"])
        sessions = [str(i) for i in range(1, 16)]
        self.session_tab.addItems(sessions)

        self.time_limit_input.setPlaceholderText("Enter")

        self.best_records_model.setHorizontalHeaderLabels(["Current_ID", "Best_Id", "", "Current", "Best "])
        self.solve_list_model.setHorizontalHeaderLabels(["ID", "#", "Time", "Ao5", "Ao12    "])

        self.best_records_view.setColumnHidden(0, True)
        self.best_records_view.setColumnHidden(1, True)
        self.solve_list_view.setColumnHidden(0, True)

        self.best_records_view.verticalHeader().setVisible(False)
        self.solve_list_view.verticalHeader().setVisible(False)

        self.best_records_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.solve_list_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        self.best_records_view.setCornerButtonEnabled(False)
        self.best_records_view.horizontalHeader().setSectionsClickable(False)

        self.best_records_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.solve_list_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.best_records_view.setMaximumWidth(160)
        self.solve_list_view.setMaximumWidth(160)

        self.scramble_label.setWordWrap(True)
        self.scramble_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.puzzle_tab.setObjectName("puzzle_tab")
        self.session_tab.setObjectName("session_tab")
        self.scramble_label.setObjectName("scramble_label")
        self.time_label.setObjectName("time_label")

        self.setStyleSheet("""
            QComboBox#puzzle_tab {
                background-color: hsl(194, 53%, 62%);
            }
            QComboBox#session_tab {
                background-color: hsl(189, 23%, 49%);
            }
            QRadioButton::indicator { 
                width: 14px; 
                height: 14px; 
                border-radius: 8px; 
                border: 2px solid hsl(189, 23%, 40%); 
                background-color: white; 
            }
            QRadioButton::indicator:hover { 
                border: 2px solid hsl(194, 53%, 62%); 
            }
            QRadioButton::indicator:checked { 
                background-color: hsl(194, 53%, 62%); 
                border: 2px solid hsl(189, 23%, 30%); 
            }
            QLabel#scramble_label {
                font-size: 30px;
                background-color: hsl(189, 23%, 49%);
            }
            QLabel#time_label {
                font-size: 120px;
                font-weight: bold;
                background-color: hsl(194, 53%, 62%);
            }
            QHeaderView:section { 
                background-color: hsl(189, 23%, 49%); 
            }
            QTableView QTableCornerButton::section {
                background-color: hsl(189, 23%, 49%);
            }
            QTableView, QPushButton {
                background-color: hsl(189, 23%, 49%);
            }
            QTableView QWidget {
                background-color: hsl(189, 23%, 49%);
            }
        """)

        for widget in [self.puzzle_tab, self.session_tab, self.time_limit_button, self.best_records_view,
                       self.solve_list_view, self.session_stats_button, self.delete_session_button]:
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    #Handles the displays and functions
    def perform(self):
        #Scamble label
        self.display_scramble()
        self.puzzle_tab.currentTextChanged.connect(self.display_scramble)

        #If time limit button is clicked
        self.display_time_limit()
        self.time_limit_button.clicked.connect(self.display_time_limit)
        self.time_limit_input.returnPressed.connect(self.time_limit_input.clearFocus)

        #Solve Timer
        self.solve_timer.timeout.connect(self.display_time)

        #Inspection Timer
        self.inspection_hold_timer.timeout.connect(self.inspection_ready)
        self.inspection_timer.timeout.connect(self.display_inspection)

        #Session Tab Switch
        self.session_tab.currentTextChanged.connect(self.update_best_records)
        self.session_tab.currentTextChanged.connect(self.display_session_stats)
        self.session_tab.currentTextChanged.connect(self.update_tab_solves)

        #Session Data delete confirmation
        self.delete_session_button.clicked.connect(self.delete_tab_data)

        #Session stats display
        self.session_stats_button.clicked.connect(self.show_stats_solves)

        #Dispaly old solves
        self.update_best_records()
        self.display_session_stats()
        self.update_tab_solves()

        #Solve list items clicked
        self.best_records_view.clicked.connect(self.show_best_info)
        self.solve_list_view.clicked.connect(self.show_solve_info)

    #Handles the press of space bar
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():

            if self.time_limit_input.hasFocus():
                super().keyPressEvent(event)
                return

            if self.solve_timer.isActive():
                self.set_visibility(True)
                self.stop_solve()

            elif self.inspection_timer.isActive():
                self.time_label.setStyleSheet("color: red;")
                self.inspection_hold_timer.start(500)

            else:
                if self.time_limit_button.isChecked():
                    try:
                        time_limit = float(self.time_limit_input.text())
                        if time_limit <= 0:
                            self.time_limit_label.setText("Time limit can never be less than or equal to 0")
                            return
                    except ValueError:
                        self.time_limit_label.setText("Enter a valid time limit (int/float only) first")
                        return

                self.set_visibility(False)
                self.time_limit_input.setVisible(False)
                self.time_limit_label.setVisible(False)
                self.start_inspection()

        super().keyPressEvent(event)

    #Handles the release of space bar
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():

            if self.inspection_is_held and self.inspection_timer.isActive():
                self.inspection_is_held = False
                self.inspection_timer.stop()
                self.time_label.setStyleSheet("color: black;")

                if self.inspection_elapsed.elapsed() > 15000:
                    self.has_inspection_penalty = True
                else:
                    self.has_inspection_penalty = False

                self.start_solve()

            else:
                self.inspection_is_held = False
                self.inspection_hold_timer.stop()

                if self.inspection_timer.isActive():
                    self.time_label.setStyleSheet("color: black;")

        super().keyReleaseEvent(event)

    #Starts solve timer
    def start_solve(self):
        self.current_raw_ms = 0
        self.time_label.setText(format_solve_time(0))
        self.solve_elapsed.start()
        self.solve_timer.start(10)

    #Stops solve timer. If time limit button is toggled, it will compare the solve time and time limit
    def stop_solve(self):
        self.solve_timer.stop()
        final_time_ms = self.solve_elapsed.elapsed()

        self.time_label.setText(format_solve_time(final_time_ms))

        if self.has_inspection_penalty:
            final_time_ms += 2000

        final_time_secs = final_time_ms / 1000.0
        if self.time_limit_button.isChecked():
            try:
                time_limit = float(self.time_limit_input.text())
                if final_time_secs <= time_limit:
                    if self.audio_loaded:
                        self.succeeded_audio.play()
                    self.time_limit_label.setStyleSheet("background-color: green")
                    self.time_limit_label.setText(f"Good job, you solved it under {time_limit}s")
                else:
                    if self.audio_loaded:
                        self.failed_audio.play()
                    self.time_limit_label.setStyleSheet("background-color: red")
                    self.time_limit_label.setText("Nice try, better luck next time.")
            except ValueError:
                self.time_limit_label.setText("Enter a valid int/float time limit.")


        self.save_solve(final_time_ms=final_time_ms, is_dnf=False)

    #Checks if inspection timer is held and ready to solve
    def inspection_ready(self):
        self.inspection_is_held = True
        self.time_label.setStyleSheet("color: Green;")

    #Inspection timer
    def start_inspection(self):
        self.has_inspection_penalty = False
        self.time_label.setText("15")
        self.inspection_elapsed.start()
        self.inspection_timer.start(10)

    #Displays solve time
    def display_time(self):
        self.current_raw_ms = self.solve_elapsed.elapsed()
        self.time_label.setText(format_solve_time(self.current_raw_ms))

    #Displays inspection time
    def display_inspection(self):
        inspection_elapsed_ms = self.inspection_elapsed.elapsed()
        inspection_left_ms = self.inspection_limit - inspection_elapsed_ms

        if inspection_left_ms <= 0:
            self.set_visibility(True)
            self.inspection_is_held = False
            self.inspection_timer.stop()
            self.inspection_hold_timer.stop()
            self.time_label.setStyleSheet("color: black;")
            self.time_label.setText("DNF")

            if self.time_limit_button.isChecked():
                if self.audio_loaded:
                    self.failed_audio.play()
                self.time_limit_label.setStyleSheet("background-color: red")
                self.time_limit_label.setText("DNF")

            self.save_solve(final_time_ms=0, is_dnf=True)

        elif inspection_left_ms <= 2000:
            if not self.inspection_hold_timer.isActive() and not self.inspection_is_held:
                self.time_label.setStyleSheet("color: hsl(33, 100%, 50%);")

            self.time_label.setText("+2")

        else:
            seconds_left = int((inspection_left_ms - 2000) / 1000)
            self.time_label.setText(str(seconds_left + 1))

    #Saves solve data
    def save_solve(self, final_time_ms, is_dnf):
        current_tab = self.session_tab.currentText()
        puzzle = self.puzzle_tab.currentText()
        final_time = final_time_ms
        scramble = self.scramble_label.text()
        has_inspection_penalty = 2 if self.has_inspection_penalty else 0
        is_dnf = 1 if is_dnf else 0
        timestamp = int(time.time())

        if self.time_limit_button.isChecked() and self.time_limit_input.text().strip():
            try:
                has_time_limit = float(self.time_limit_input.text())
            except ValueError:
                has_time_limit = 0.0
        else:
            has_time_limit = 0.0

        solve = Solve(tab= current_tab, puzzle= puzzle, final_time_ms= final_time,
                      scramble= scramble, has_inspection_penalty= has_inspection_penalty,
                      is_dnf= is_dnf, has_time_limit= has_time_limit, timestamp= timestamp)

        data_dict = solve.data_dict()
        insert_solve_data(data_dict)

        tab_data = fetch_tab_data(current_tab=current_tab, order="DESC")

        self.insert_row(tab_data= tab_data)
        self.display_scramble()

    #Inserts new solve
    def insert_row(self, tab_data):
        puzzle = self.puzzle_tab.currentText()
        current_tab = self.session_tab.currentText()

        newest_data = tab_data[0]

        time_secs = check_solve_time(newest_data)

        ao5 = "-"
        ao12 = "-"

        if len(tab_data) >= 5:
            ao5_list = tab_data[0:5]
            ao5_ave = calculate_wca_average(ao5_list)
            ao5 = format_solve_time(ao5_ave)

            if isinstance(ao5_ave, int):
                update_average_best("Ao5", puzzle, current_tab, ao5_list[0]["tab_id"], ao5_ave)

        if len(tab_data) >= 12:
            ao12_list = tab_data[0:12]
            ao12_ave = calculate_wca_average(ao12_list)
            ao12 = format_solve_time(ao12_ave)

            if isinstance(ao12_ave, int):
                update_average_best("Ao12", puzzle, current_tab, ao12_list[0]["tab_id"], ao12_ave)

        if len(tab_data) >= 100:
            ao100_list = tab_data[0:100]
            ao100_ave = calculate_wca_ao100(ao100_list)
            ao100 = format_solve_time(ao100_ave)

            if isinstance(ao100_ave, int):
                update_average_best("Ao100", puzzle, current_tab, ao100_list[0]["tab_id"], ao100_ave)

        row_col1 = QStandardItem(str(newest_data["tab_id"]))
        row_col2 = QStandardItem(str(len(tab_data)))
        row_col3 = QStandardItem(time_secs)
        row_col4 = QStandardItem(ao5)
        row_col5 = QStandardItem(ao12)

        solve_row = [row_col1, row_col2, row_col3, row_col4, row_col5]
        self.solve_list_model.insertRow(0, solve_row)

        #Updates best records table
        self.display_best_records(tab_data)
        #For session mean and total solve
        self.display_session_stats()

    #Display best records
    def display_best_records(self, tab_data):
        puzzle = self.puzzle_tab.currentText()
        current_tab = self.session_tab.currentText()

        current_solve = tab_data[0]

        time_secs = check_solve_time(current_solve)

        best_ao5 = "-"
        best_ao12 = "-"
        best_ao100 = "-"

        best_ao5_id = "-"
        best_ao12_id = "-"
        best_ao100_id = "-"

        # For the single best records display
        single_best_data = fetch_single_best(current_tab)
        if single_best_data is not None:
            single_row = [
                QStandardItem(str(current_solve["tab_id"])),
                QStandardItem(str(single_best_data["tab_id"])),
                QStandardItem("Single"),
                QStandardItem(time_secs),
                QStandardItem(format_solve_time(single_best_data["final_time_ms"]))
            ]

            for column, item in enumerate(single_row):
                self.best_records_model.setItem(0, column, item)

        # For the ao5 best records display
        if len(tab_data) >= 5:
            last_ao5_ave = calculate_wca_average(tab_data[0:5])
            current_ao5 = format_solve_time(last_ao5_ave)

            best_ao5_data = fetch_average_best("Ao5", puzzle, current_tab)
            if best_ao5_data is not None:
                best_ao5 = format_solve_time(int(best_ao5_data["average"]))
                best_ao5_id = str(best_ao5_data["tab_id"])

            ao5_row = [
                QStandardItem(str(current_solve["tab_id"])),
                QStandardItem(best_ao5_id),
                QStandardItem("Ao5"),
                QStandardItem(current_ao5),
                QStandardItem(best_ao5)
            ]

            for column, item in enumerate(ao5_row):
                self.best_records_model.setItem(1, column, item)

        # For the ao12 best records display
        if len(tab_data) >= 12:
            last_ao12_ave = calculate_wca_average(tab_data[0:12])
            current_ao12 = format_solve_time(last_ao12_ave)

            best_ao12_data = fetch_average_best("Ao12", puzzle, current_tab)
            if best_ao12_data is not None:
                best_ao12 = format_solve_time(int(best_ao12_data["average"]))
                best_ao12_id = str(best_ao12_data["tab_id"])

            ao12_row = [
                QStandardItem(str(current_solve["tab_id"])),
                QStandardItem(best_ao12_id),
                QStandardItem("Ao12"),
                QStandardItem(current_ao12),
                QStandardItem(best_ao12)
            ]

            for column, item in enumerate(ao12_row):
                self.best_records_model.setItem(2, column, item)

        #For the ao100 best records display
        if len(tab_data) >= 100:
            last_ao100_ave = calculate_wca_ao100(tab_data[0:100])
            current_ao100 = format_solve_time(last_ao100_ave)

            best_ao100_data = fetch_average_best("Ao100", puzzle, current_tab)
            if best_ao100_data is not None:
                best_ao100 = format_solve_time(int(best_ao100_data["average"]))
                best_ao100_id = str(best_ao100_data["tab_id"])

            ao100_row = [
                QStandardItem(str(current_solve["tab_id"])),
                QStandardItem(best_ao100_id),
                QStandardItem("Ao100"),
                QStandardItem(current_ao100),
                QStandardItem(best_ao100)
            ]

            for column, item in enumerate(ao100_row):
                self.best_records_model.setItem(3, column, item)

    #Calculates and displays the session solves and mean
    def display_session_stats(self):
        current_tab = self.session_tab.currentText()

        tab_data = fetch_tab_data(current_tab)

        session_mean_ms, total_solves = calculate_session_mean(tab_data)

        if isinstance(session_mean_ms, int):
            session_mean_secs = format_solve_time(session_mean_ms)
        else:
            session_mean_secs = "-"

        self.session_stats_button.setText(f"Total solves: {total_solves}/{len(tab_data)}\n"
                                          f"Mean: {session_mean_secs}")

    #Updates best records by looping through all the tab solves
    def update_best_records(self):
        self.best_records_model.removeRows(0, self.best_records_model.rowCount())

        current_tab = self.session_tab.currentText()
        puzzle = self.puzzle_tab.currentText()

        tab_data = fetch_tab_data(current_tab, order="ASC")
        single_best_data = fetch_single_best(current_tab)

        if not tab_data or single_best_data is None:
            return

        #Get Newest/Latest Solve
        latest_solve = tab_data[-1]

        single_best = check_solve_time(single_best_data)

        single_best_row = [QStandardItem(str(latest_solve["tab_id"])),
                           QStandardItem(str(single_best_data["tab_id"])),
                           QStandardItem("Single"),
                           QStandardItem(check_solve_time(latest_solve)),
                           QStandardItem(single_best)]
        self.best_records_model.appendRow(single_best_row)

        current_ao5 = "-"
        current_ao12 = "-"
        current_ao100 = "-"

        best_ao5 = "-"
        best_ao12 = "-"
        best_ao100 = "-"

        best_ao5_id = "-"
        best_ao12_id = "-"
        best_ao100_id = "-"

        #Loop through all the tab solves and updates best average
        store_average_best(tab_data, puzzle, current_tab)

        if len(tab_data) >= 5:
            last_ao5_ave = calculate_wca_average(tab_data[-5:])
            current_ao5 = format_solve_time(last_ao5_ave)

            best_ao5_data = fetch_average_best("Ao5", puzzle, current_tab)
            if best_ao5_data is not None:
                best_ao5 = format_solve_time(int(best_ao5_data["average"]))
                best_ao5_id = str(best_ao5_data["tab_id"])

            ao5_row = [QStandardItem(str(latest_solve["tab_id"])),
                       QStandardItem(best_ao5_id),
                       QStandardItem("Ao5"),
                       QStandardItem(current_ao5),
                       QStandardItem(best_ao5)]
            self.best_records_model.appendRow(ao5_row)

        if len(tab_data) >= 12:
            last_ao12_ave = calculate_wca_average(tab_data[-12:])
            current_ao12 = format_solve_time(last_ao12_ave)

            best_ao12_data = fetch_average_best("Ao12", puzzle, current_tab)
            if best_ao12_data is not None:
                best_ao12 = format_solve_time(int(best_ao12_data["average"]))
                best_ao12_id = str(best_ao12_data["tab_id"])

            ao12_row = [QStandardItem(str(latest_solve["tab_id"])),
                        QStandardItem(best_ao12_id),
                        QStandardItem("Ao12"),
                        QStandardItem(current_ao12),
                        QStandardItem(best_ao12)]
            self.best_records_model.appendRow(ao12_row)

        if len(tab_data) >= 100:
            last_ao100_ave = calculate_wca_ao100(tab_data[-100:])
            current_ao100 = format_solve_time(last_ao100_ave)

            best_ao100_data = fetch_average_best("Ao100", puzzle, current_tab)
            if best_ao100_data is not None:
                best_ao100 = format_solve_time(int(best_ao100_data["average"]))
                best_ao100_id = str(best_ao100_data["tab_id"])

            ao100_row = [QStandardItem(str(latest_solve["tab_id"])),
                        QStandardItem(best_ao100_id),
                        QStandardItem("Ao100"),
                        QStandardItem(current_ao100),
                        QStandardItem(best_ao100)]
            self.best_records_model.appendRow(ao100_row)

    #Updates tab solve list by looping through all the tab solves
    def update_tab_solves(self):
        self.solve_list_model.removeRows(0, self.solve_list_model.rowCount())

        current_tab = self.session_tab.currentText()
        tab_data = fetch_tab_data(current_tab= current_tab, order="ASC")

        i = 1
        for index, data in enumerate(tab_data):

            time_secs = check_solve_time(data)

            ao5 = "-"
            ao12 = "-"

            if index >= 4:
                ao5_list = tab_data[index - 4: index + 1]
                ao5_ave = calculate_wca_average(ao5_list)
                ao5 = format_solve_time(ao5_ave)

            if index >= 11:
                ao12_list = tab_data[index - 11: index + 1]
                ao12_ave = calculate_wca_average(ao12_list)
                ao12 = format_solve_time(ao12_ave)

            solve_row = [QStandardItem(str(data["tab_id"])),
                         QStandardItem(str(i)),
                         QStandardItem(time_secs),
                         QStandardItem(ao5),
                         QStandardItem(ao12)]
            self.solve_list_model.insertRow(0, solve_row)
            i += 1

    #Deletes the tab data
    def delete_tab_data(self):
        current_tab = self.session_tab.currentText()
        puzzle = self.puzzle_tab.currentText()

        confirm_delete_box = QMessageBox(self)
        confirm_delete_box.setWindowTitle("Confirm Deletion")
        confirm_delete_box.setIcon(QMessageBox.Icon.Warning)
        confirm_delete_box.setText("<b>Are you sure you want to delete the current tab data?</b>")
        confirm_delete_box.setInformativeText("This action cannot be undone.")

        confirm_delete_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_delete_box.setDefaultButton(QMessageBox.StandardButton.No)

        user = confirm_delete_box.exec()

        if user == QMessageBox.StandardButton.Yes:
            clear_average_data(puzzle, current_tab)
            clear_tab_data(current_tab)
            self.best_records_model.removeRows(0, self.best_records_model.rowCount())
            self.solve_list_model.removeRows(0, self.solve_list_model.rowCount())
            self.session_stats_button.setText("Solve:\nMean: ")
        else:
            return

    #Shows the stats of the clicked item in best records
    def show_best_info(self, index):
        current_tab = self.session_tab.currentText()
        row = index.row()
        column = index.column()

        tab_data = fetch_tab_data(current_tab)
        if not tab_data:
            return

        current_single_tab_id = self.best_records_model.item(row, 0).text()
        best_single_tab_id = self.best_records_model.item(row, 1).text()

        best_ao5_tab_id = self.best_records_model.item(row, 1).text()
        best_ao12_tab_id = self.best_records_model.item(row, 1).text()
        best_ao100_tab_id = self.best_records_model.item(row, 1).text()

        solve_info_box = QMessageBox(self)
        solve_info_browser = QTextBrowser()

        solve_info_box.setWindowTitle("Solve Statistics")

        layout = solve_info_box.layout()
        layout.addWidget(solve_info_browser)

        solve_info_browser.setMinimumHeight(180)
        solve_info_browser.setMinimumWidth(320)

        solve_info_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        if row == 0 and column == 3:
            solve_data = fetch_data_by_id(current_tab, int(current_single_tab_id))

            if solve_data is not None:
                solve_time = check_solve_time(solve_data)

                puzzle = solve_data["puzzle"]
                scramble = solve_data["scramble"]

                timestamp = solve_data["timestamp"]
                timestamp_obj = datetime.fromtimestamp(timestamp)
                readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                details = f"""
                    <b>Current solve</b><br>
                    <b>Date solved:</b> {readable_time}<br>
                    <b>Puzzle:</b> {puzzle}<br>
                    <b>Current Solve time:</b> {solve_time}<br>
                    <b>Scramble:</b> {scramble}<br>
                """
                solve_info_browser.setHtml(details)
                solve_info_box.exec()

        elif row == 0 and column == 4:
            solve_data = fetch_data_by_id(current_tab, int(best_single_tab_id))

            if solve_data is not None:
                solve_time = check_solve_time(solve_data)

                puzzle = solve_data["puzzle"]
                scramble = solve_data["scramble"]

                timestamp = solve_data["timestamp"]
                timestamp_obj = datetime.fromtimestamp(timestamp)
                readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                details = f"""
                                <b>Personal Best</b><br>
                                <b>Date solved:</b> {readable_time}<br>
                                <b>Puzzle:</b> {puzzle}<br>
                                <b>Solve time:</b> {solve_time}<br>
                                <b>Scramble:</b> {scramble}<br>
                            """
                solve_info_browser.setHtml(details)
                solve_info_box.exec()

        elif row == 1 and column == 3:
            current_ao5 = self.best_records_model.data(index)
            current_ao5_data = tab_data[0:5]
            if len(current_ao5_data) == 5:
                current_ao5_list = get_solve_list(current_ao5_data)
                timestamp = current_ao5_data[0]["timestamp"]
                timestamp_obj = datetime.fromtimestamp(timestamp)
                readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                details = f"""<b>Current Average of 5:</b> {current_ao5}<br>
                            <b>Date:</b> {readable_time}<br><br>
                        """

                for i, solve in enumerate(current_ao5_list):
                    solve_time = solve[0]
                    scramble = solve[1]

                    details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                solve_info_browser.setHtml(details)
                solve_info_box.exec()

        elif row == 1 and column == 4:
            best_ao5 = self.best_records_model.data(index)

            if best_ao5_tab_id == "-":
                return

            best_ao5_id_int = int(best_ao5_tab_id)

            #Something I learned in finding a specific index
            target_index = next((i for i, data in enumerate(tab_data) if int(data["tab_id"]) == best_ao5_id_int), None)

            if target_index is not None:
                best_ao5_data = tab_data[target_index: target_index + 5]

                if len(best_ao5_data) == 5:
                    best_ao5_list = get_solve_list(best_ao5_data)
                    timestamp = best_ao5_data[0]["timestamp"]
                    timestamp_obj = datetime.fromtimestamp(timestamp)
                    readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                    details = f"""<b>Best Average of 5:</b> {best_ao5}<br>
                                <b>Date:</b> {readable_time}<br><br>
                        """

                    for i, solve in enumerate(best_ao5_list):
                        solve_time = solve[0]
                        scramble = solve[1]
                        details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                    solve_info_browser.setHtml(details)
                    solve_info_box.exec()

        elif row == 2 and column == 3:
            current_ao12 = self.best_records_model.data(index)
            current_ao12_data = tab_data[0:12]

            if len(current_ao12_data) == 12:
                current_ao12_list = get_solve_list(current_ao12_data)
                timestamp = current_ao12_data[0]["timestamp"]
                timestamp_obj = datetime.fromtimestamp(timestamp)
                readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                details = f"""<b>Current Average of 12:</b> {current_ao12}<br>
                            <b>Date:</b> {readable_time}<br><br>
                    """

                for i, solve in enumerate(current_ao12_list):
                    solve_time = solve[0]
                    scramble = solve[1]

                    details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                solve_info_browser.setHtml(details)
                solve_info_box.exec()

        elif row == 2 and column == 4:
            best_ao12 = self.best_records_model.data(index)

            if best_ao12_tab_id == "-":
                return

            best_ao12_id_int = int(best_ao12_tab_id)

            target_index = next((i for i, data in enumerate(tab_data) if int(data["tab_id"]) == best_ao12_id_int), None)

            if target_index is not None:
                best_ao12_data = tab_data[target_index: target_index + 12]

                if len(best_ao12_data) == 12:
                    best_ao12_list = get_solve_list(best_ao12_data)
                    timestamp = best_ao12_data[0]["timestamp"]
                    timestamp_obj = datetime.fromtimestamp(timestamp)
                    readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                    details = f"""<b>Best Average of 12:</b> {best_ao12}<br>
                                <b>Date:</b> {readable_time}<br><br>
                        """

                    for i, solve in enumerate(best_ao12_list):
                        solve_time = solve[0]
                        scramble = solve[1]
                        details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                    solve_info_browser.setHtml(details)
                    solve_info_box.exec()

        elif row == 3 and column == 3:
            current_ao100 = self.best_records_model.data(index)
            current_ao100_data = tab_data[0:100]

            if len(current_ao100_data) == 100:
                current_ao100_list = get_solve_list(current_ao100_data)
                timestamp = current_ao100_data[0]["timestamp"]
                timestamp_obj = datetime.fromtimestamp(timestamp)
                readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                details = f"""<b>Current Average of 100:</b> {current_ao100}<br>
                                        <b>Date:</b> {readable_time}<br><br>
                                """

                for i, solve in enumerate(current_ao100_list):
                    solve_time = solve[0]
                    scramble = solve[1]

                    details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                solve_info_browser.setHtml(details)
                solve_info_box.exec()

        elif row == 3 and column == 4:
            best_ao100 = self.best_records_model.data(index)

            if best_ao100_tab_id == "-":
                return

            best_ao100_id_int = int(best_ao100_tab_id)

            target_index = next((i for i, data in enumerate(tab_data) if int(data["tab_id"]) == best_ao100_id_int), None)

            if target_index is not None:
                best_ao100_data = tab_data[target_index: target_index + 100]

                if len(best_ao100_data) == 100:
                    best_ao100_list = get_solve_list(best_ao100_data)
                    timestamp = best_ao100_data[0]["timestamp"]
                    timestamp_obj = datetime.fromtimestamp(timestamp)
                    readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                    details = f"""<b>Best Average of 100:</b> {best_ao100}<br>
                                            <b>Date:</b> {readable_time}<br><br>
                                    """

                    for i, solve in enumerate(best_ao100_list):
                        solve_time = solve[0]
                        scramble = solve[1]
                        details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                    solve_info_browser.setHtml(details)
                    solve_info_box.exec()

    #Shows the total solves and mean of the tab
    def show_stats_solves(self):
        puzzle = self.puzzle_tab.currentText()
        current_tab = self.session_tab.currentText()

        tab_data = fetch_tab_data(current_tab, order="ASC")

        session_mean_ms, total_solves = calculate_session_mean(tab_data)

        if isinstance(session_mean_ms, int):
            session_mean_secs = format_solve_time(session_mean_ms)
        else:
            session_mean_secs = "-"


        solve_info_box = QMessageBox(self)
        solve_info_browser = QTextBrowser()

        solve_info_box.setWindowTitle("Solve Statistics")

        layout = solve_info_box.layout()
        layout.addWidget(solve_info_browser)

        solve_info_browser.setMinimumHeight(180)
        solve_info_browser.setMinimumWidth(320)

        solve_info_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        details = f"<b>Total solves:</b> {total_solves}/{len(tab_data)}<br><b>Mean:</b> {session_mean_secs}<br><br>"

        for index, data in enumerate(tab_data):

            solve_time = check_solve_time(data)
            scramble = data["scramble"]

            details += f"{index + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

        solve_info_browser.setHtml(details)
        solve_info_box.exec()

    #Shows the stats of the clicked item in solve list
    def show_solve_info(self, index):
        current_tab = self.session_tab.currentText()
        row = index.row()
        column = index.column()

        tab_id = self.solve_list_model.item(row, 0).text()

        solve_info_box = QMessageBox(self)
        solve_info_browser = QTextBrowser()

        solve_info_box.setWindowTitle("Solve Statistics")

        layout = solve_info_box.layout()
        layout.addWidget(solve_info_browser)

        solve_info_browser.setMinimumHeight(180)
        solve_info_browser.setMinimumWidth(320)

        solve_info_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        if column in [1, 2]:
            solve_data = fetch_data_by_id(current_tab, int(tab_id))

            if solve_data is not None:
                solve_time = check_solve_time(solve_data)

                puzzle = solve_data["puzzle"]
                scramble = solve_data["scramble"]

                timestamp = solve_data["timestamp"]
                timestamp_obj = datetime.fromtimestamp(timestamp)
                readable_time = timestamp_obj.strftime("%B %d, %Y - %I:%M %p")

                details = f"""
                    <b>Date solved:</b> {readable_time}<br>
                    <b>Puzzle:</b> {puzzle}<br>
                    <b>Solve time:</b> {solve_time}<br>
                    <b>Scramble:</b> {scramble}<br>
                """
                solve_info_browser.setHtml(details)

                solve_info_box.setStandardButtons(QMessageBox.StandardButton.NoButton)

                plus_two_button = solve_info_box.addButton("+2", QMessageBox.ButtonRole.ActionRole)
                dnf_button = solve_info_box.addButton("DNF", QMessageBox.ButtonRole.ActionRole)
                delete_button = solve_info_box.addButton("Delete Solve", QMessageBox.ButtonRole.DestructiveRole)
                ok_button = solve_info_box.addButton("Ok", QMessageBox.ButtonRole.AcceptRole)

                solve_info_box.exec()

                user = solve_info_box.clickedButton()

                inspection_status = solve_data["has_inspection_penalty"]
                dnf_status = solve_data["is_dnf"]

                if user == plus_two_button:
                    if dnf_status == 1 and solve_data["final_time_ms"] == 0:
                        return

                    plus_two_solve(current_tab, int(tab_id), solve_data["final_time_ms"], inspection_status, dnf_status)

                elif user == dnf_button:
                    if dnf_status == 1 and solve_data["final_time_ms"] == 0:
                        return

                    dnf_solve(current_tab, int(tab_id), solve_data["final_time_ms"], inspection_status, dnf_status)

                elif user == delete_button:
                    confirm = QMessageBox.question(self, "Confirm Deletion",
                                                   "Are you sure you want to permanently delete this specific solve?",
                                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                   QMessageBox.StandardButton.No)
                    if confirm == QMessageBox.StandardButton.Yes:
                        delete_data_by_id(current_tab, int(tab_id))
                else:
                    return

                clear_average_data(puzzle, current_tab)
                self.update_best_records()
                self.display_session_stats()
                self.update_tab_solves()

        elif column == 3:
            ao5 = self.solve_list_model.data(index)
            tab_data = fetch_tab_data(current_tab)
            ao5_data = tab_data[row: row + 5]
            if len(ao5_data) == 5:
                ao5_list = get_solve_list(ao5_data)

                details = f"<b>Average of 5: {ao5}</b><br><br>"

                for i, solve in enumerate(ao5_list):
                    solve_time = solve[0]
                    scramble = solve[1]

                    details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                solve_info_browser.setHtml(details)
                user = solve_info_box.exec()

        elif column == 4:
            ao12 = self.solve_list_model.data(index)
            tab_data = fetch_tab_data(current_tab)
            ao12_data = tab_data[row: row + 12]
            if len(ao12_data) == 12:
                ao12_list = get_solve_list(ao12_data)

                details = f"<b>Average of 12: {ao12}</b><br><br>"

                for i, solve in enumerate(ao12_list):
                    solve_time = solve[0]
                    scramble = solve[1]

                    details += f"{i + 1}. <b>{solve_time}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {scramble}<br>"

                solve_info_browser.setHtml(details)
                user = solve_info_box.exec()

    #Updates and display the scramble
    def display_scramble(self):
        #Gets the current puzzle tab and generate scramble
        puzzle = self.puzzle_tab.currentText()
        combination = generate_scramble(puzzle)
        self.scramble_label.setText(combination)

    #Displays time limit input and label
    def display_time_limit(self):
        if self.time_limit_button.isChecked():
            for widget in [self.time_limit_input, self.time_limit_label]:
                widget.setVisible(True)
        else:
            for widget in [self.time_limit_input, self.time_limit_label]:
                widget.setVisible(False)

    #Shows/Hide visibility of specific widgets
    def set_visibility(self, status):
        for widget in [self.puzzle_tab, self.time_limit_button, self.scramble_label,
                       self.session_tab, self.delete_session_button, self.best_records_view,
                       self.session_stats_button, self.solve_list_view]:
            widget.setVisible(status)
        self.display_time_limit()


if __name__ == '__main__':
    init_db()
    app = QApplication(sys.argv)
    speed_cube_timer = SpeedCubeTimer()
    speed_cube_timer.show()
    sys.exit(app.exec())