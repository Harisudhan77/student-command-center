import PySide6
from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,QFrame,QDialog,QDateTimeEdit,QLineEdit,QFormLayout,QProgressBar,QScrollArea,QCheckBox,QMessageBox
import sys
from PySide6.QtCore import Qt,QDateTime

app =QApplication(sys.argv)

main_window = QMainWindow()
main_window.setWindowTitle("Student Command Center")
main_window.resize(1000,650)

exams = []
tasks = []
completed_tasks = []

def open_exam_dialog() :
    dialog=QDialog()
    dialog.setWindowTitle("Add new exam")
    dialog.setFixedSize(350,250)

    layout = QVBoxLayout(dialog)
    form = QFormLayout()

    subject_input = QLineEdit()
    subject_input.setPlaceholderText("Enter the subject name")

    exam_datetime = QDateTimeEdit()
    exam_datetime.setCalendarPopup(True)
    exam_datetime.setDateTime(QDateTime.currentDateTime())

    form.addRow("Subject:",subject_input)
    form.addRow("Exam Date & Time:",exam_datetime)

    layout.addLayout(form)

    buttons_layout = QHBoxLayout()

    save_btn = QPushButton("Save Exam")
    cancel_btn = QPushButton("cancel")

    buttons_layout.addWidget(save_btn)
    buttons_layout.addWidget(cancel_btn)

    layout.addLayout(buttons_layout)

    def save_exam ():
        subject = subject_input.text().strip()
        exam_date = exam_datetime.dateTime()

        if subject:
            exams.append({
                "subject": subject,
                "datetime": exam_date
            })
            refresh_exam_reminder()
            exam_no.setText(str(len(exams)))
            exam_subtitle.setText(
                f"Next: {subject} "
            )
            dialog.accept()

    save_btn.clicked.connect(save_exam)
    cancel_btn.clicked.connect(dialog.reject)

    dialog.exec()


def open_tasks_dialog() :
    dialog=QDialog()
    dialog.setWindowTitle("Add new task")
    dialog.setFixedSize(350,250)

    layout = QVBoxLayout(dialog)
    form = QFormLayout()

    task_input = QLineEdit()
    task_input.setPlaceholderText("Enter the task name")

    task_datetime = QDateTimeEdit()
    task_datetime.setCalendarPopup(True)
    task_datetime.setDateTime(QDateTime.currentDateTime())

    form.addRow("Task:",task_input)
    form.addRow("Deadline Date & Time:",task_datetime)

    layout.addLayout(form)

    buttons_layout = QHBoxLayout()

    save_btn = QPushButton("Save Task")
    cancel_btn = QPushButton("cancel")

    buttons_layout.addWidget(save_btn)
    buttons_layout.addWidget(cancel_btn)

    layout.addLayout(buttons_layout)
    
    def save_task ():
        task = task_input.text().strip()
        deadline_date = task_datetime.dateTime()

        if task:
            tasks.append({
                "task": task,
                "datetime": deadline_date
            })
            refresh_pending_tasks()

            dialog.accept()

    save_btn.clicked.connect(save_task)
    cancel_btn.clicked.connect(dialog.reject)

    dialog.exec()

def refresh_exam_reminder ():
    upcoming_exams = [
        exam for exam in exams
        if exam["datetime"] >= QDateTime.currentDateTime()
    ]
    if not upcoming_exams:
        reminder_subject.setText("No upcoming exams")
        reminder_date.setText("Add an exam to see its date")
        reminder_countdown.setText("You're all caught up")
        return
    
    next_exam = min(
        upcoming_exams,
        key = lambda exam: exam["datetime"]
    )
    exam_subject = next_exam["subject"]
    exam_datetime = next_exam["datetime"]

    days_left = QDateTime.currentDateTime().daysTo(exam_datetime)
    reminder_subject.setText(exam_subject)

    reminder_date.setText(exam_datetime.toString("dd MM yyyy | hh:mm AP"))

    if days_left == 0:
        reminder_countdown.setText("Your exam is today !")
    elif days_left == 1:
        reminder_countdown.setText("Your exam is tomorrow !")
    else:
        reminder_countdown.setText(f"{days_left} days remaining")
    
main_widget = QWidget()
main_window.setCentralWidget(main_widget)
main_widget.setStyleSheet("background-color : #111827 ;")
main_layout=QHBoxLayout()
main_layout.setContentsMargins(0,0,0,0)
main_layout.setSpacing(0)
main_widget.setLayout(main_layout)

sidebar = QWidget()
sidebar.setFixedWidth(220)
sidebar.setStyleSheet("""
           background-color : #0B1220 ;
           border-radius : 14px
""")
sidebar_layout = QVBoxLayout(sidebar)
sidebar_layout.setContentsMargins(18,25,18,18)

brand=QLabel("STUDY HUB")
brand.setStyleSheet("""
           color : #FFFFFF;
           font-size : 33px;
           font-weight : bold

""")
sidebar_layout.addWidget(brand)
sidebar_layout.addSpacing(40)

top_line = QFrame()
top_line.setFrameShape(QFrame.Shape.HLine)
top_line.setStyleSheet(""" 
        
            background-color: #334155;
            border: none;
            max-height: 1px;

""")
sidebar_layout.addWidget(top_line)
sidebar_layout.addSpacing(15)

menu_label = QLabel("MAIN MENU")
menu_label.setStyleSheet(""" 

                color: #64748B;
                font-size: 11px;
                font-weight: bold;
                padding-left: 10px;
""")
sidebar_layout.addWidget(menu_label)
sidebar_layout.addSpacing(8)

dashboard_btn = QPushButton("📊 Dashboard")
tasks_btn = QPushButton("📋 Tasks")
subjects_btn = QPushButton("📚 Subjects")
exams_btn = QPushButton("🎯 Exams")
progress_btn = QPushButton("📈 Progress")
settings_btn = QPushButton("⚙️ Settings")

buttons = [
    dashboard_btn,
    tasks_btn,
    subjects_btn,
    exams_btn,
    progress_btn
]

for button in buttons:
    button.setFixedHeight(48)
    button.setStyleSheet("""
               
                QPushButton {

                      color: #CBD5E1;
                      background-color: transparent;
                      border: none;
                      border-radius: 9px;
                      text-align: left;
                      padding-left: 14px;
                      font-size: 15px;
                      font-weight: 500;
                }

                QPushButton:hover {
                      background-color:#663399;
                      color: #FFFFFF;
                
                }

 """)

    sidebar_layout.addWidget(button)
sidebar_layout.addStretch()

top_line = QFrame()
top_line.setFrameShape(QFrame.Shape.HLine)
top_line.setStyleSheet(""" 
        
            background-color: #334155;
            border: none;
            max-height: 1px;

""")
sidebar_layout.addWidget(top_line)
sidebar_layout.addSpacing(15)

ai_label = QLabel("AI FEATURES")
ai_label.setStyleSheet(""" 

                color: #64748B;
                font-size: 11px;
                font-weight: bold;
                padding-left: 10px;
""")
sidebar_layout.addWidget(ai_label)
sidebar_layout.addSpacing(8)

ai_btn = QPushButton("🤖 Study Buddy AI")
planner_btn = QPushButton("📆 Study Planner")
sidebar_layout.addWidget(ai_btn)
sidebar_layout.addWidget(planner_btn)
planner_btn.setFixedHeight(48)
ai_btn.setFixedHeight(48)
planner_btn.setStyleSheet(""" 
                QPushButton {

                      color: #CBD5E1;
                      background-color: transparent;
                      border: none;
                      border-radius: 9px;
                      text-align: left;
                      padding-left: 14px;
                      font-size: 15px;
                      font-weight: 500;
                }

                QPushButton:hover {
                      background-color:#663399;
                      color: FFFFFF;
                
                }

""")
ai_btn.setStyleSheet(""" 
                QPushButton {

                      color: #CBD5E1;
                      background-color: transparent;
                      border: none;
                      border-radius: 9px;
                      text-align: left;
                      padding-left: 14px;
                      font-size: 15px;
                      font-weight: 500;
                }

                QPushButton:hover {
                      background-color:#663399;
                      color: #FFFFFF;
                
                }

""")
sidebar_layout.addStretch()


def open_study_buddy():
    """Open the Study Buddy AI chat (Groq + GPT-OSS)."""
    try:
        from study_buddy import StudyBuddyDialog
    except Exception as error:
        QMessageBox.critical(
            main_window,
            "Study Buddy AI",
            "Could not load the Study Buddy module.\n\n"
            f"{error}\n\n"
            "Install the dependencies with:\n"
            "    pip install groq python-dotenv",
        )
        return

    StudyBuddyDialog(main_window).exec()


ai_btn.clicked.connect(open_study_buddy)


bottom_line = QFrame()
bottom_line.setFrameShape(QFrame.Shape.HLine)
bottom_line.setStyleSheet(""" 
               
                background-color: #334155;
                border: none;
                max-height: 1px;

""")
sidebar_layout.addWidget(bottom_line)
sidebar_layout.addWidget(settings_btn)
settings_btn.setFixedHeight(48)
settings_btn.setStyleSheet(""" 
                QPushButton {

                      color: #CBD5E1;
                      background-color: transparent;
                      border: none;
                      border-radius: 9px;
                      text-align: left;
                      padding-left: 14px;
                      font-size: 15px;
                      font-weight: 500;
                }

                QPushButton:hover {
                      background-color:#663399;
                      color: #FFFFFF;
                
                }

""")


main_layout.addWidget(sidebar)

scroll_area = QScrollArea()
scroll_area.setWidgetResizable(True)
scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
scroll_area.setStyleSheet("""
      QScrollArea {
            border: none;
            background-color: #1D2130;
      }
""")

content_area = QWidget()
content_layout = QVBoxLayout(content_area)

content_layout.setContentsMargins(30,25,30,25)
content_layout.setSpacing(20)

content_area.setStyleSheet("background-color: #1D2130;")

scroll_area.setWidget(content_area)
main_layout.addWidget(scroll_area,1)

name_label = QLabel("STUDENT COMMAND CENTRE")
name_label.setStyleSheet("""
                color: #dda0dd;
                font-size: 10px;
                font-weight: italic;
                padding-left: 20px;
 """)
content_layout.addWidget(name_label)

welcome_label = QLabel("Welcome Back ! 👋")
welcome_label.setStyleSheet("""
                color: #FFFFFF;
                font-size: 28px;
                font-weight: bold;
                padding-left: 14px;
 """)
content_layout.addWidget(welcome_label)

quote_label = QLabel("Let's make today productive !")
quote_label.setStyleSheet(""" 

                color: #64748B;
                font-size: 15px;
                padding-left: 20px;
""")
content_layout.addWidget(quote_label)

cards_row = QHBoxLayout()

exam_card = QWidget()
exam_card.setObjectName("examCard")
exam_card.setMinimumHeight(190)

exam_card.setStyleSheet(""" 
        QWidget#examCard {
             background-color: #172338;
             border: 1px solid #2B3A52;
             border-radius: 16px;
        }
""")

exam_card_layout = QVBoxLayout(exam_card)
exam_card_layout.setContentsMargins(22,18,22,18)
exam_card_layout.setSpacing(8)

exam_header = QHBoxLayout()

exam_title= QLabel("UPCOMING EXAMS !")
exam_title.setStyleSheet(""" 
  
            color: #94A3B8;
            font-size: 12px;
            font-weight: bold;
            background-color: transparent;
            border: none;
""")

add_exam_btn = QPushButton("+")
add_exam_btn.setFixedSize(36,36)
add_exam_btn.setStyleSheet(""" 

        QPushButton {
            color: white;
            background-color: #6D5AE6;
            border: none;
            border-radius: 18px;
            font-size: 23px;
            font-weight: bold;
        }

        QPushButton:hover {
                 background-color: #8170F0;        
        }

""")
add_exam_btn.clicked.connect(open_exam_dialog)

exam_header.addWidget(exam_title)
exam_header.addStretch()
exam_header.addWidget(add_exam_btn)

exam_card_layout.addLayout(exam_header)

exam_no = QLabel("0")
exam_no.setStyleSheet(""" 

        color: #F8FAFC;
        font-size: 40px;
        font-weight: bold;
        background-color: transparent;
        border: none;

""")

exam_subtitle= QLabel("No pending exams")
exam_subtitle.setStyleSheet(""" 

        color: #AAB7CC;
        font-size: 14px;
        background-color: transparent;
        border: none;

""")

exam_card_layout.addWidget(exam_no)
exam_card_layout.addWidget(exam_subtitle)

cards_row.setSpacing(20)
cards_row.addWidget(exam_card)

tasks_card= QWidget()
tasks_card.setObjectName("tasksCard")
tasks_card.setMinimumHeight(190)

tasks_card.setStyleSheet(""" 
        QWidget#tasksCard {
             background-color: #172338;
             border: 1px solid #2B3A52;
             border-radius: 16px;
        }
""")

tasks_card_layout = QVBoxLayout(tasks_card)
tasks_card_layout.setContentsMargins(22,18,22,18)
tasks_card_layout.setSpacing(8)

tasks_title= QLabel("TASKS COMPLETED")
tasks_title.setStyleSheet(""" 
  
            color: #94A3B8;
            font-size: 12px;
            font-weight: bold;
            background-color: transparent;
            border: none;

""")

tasks_header =QHBoxLayout()

tasks_header.addWidget(tasks_title)
tasks_header.addStretch()

add_tasks_btn = QPushButton("+")
add_tasks_btn.setFixedSize(36,36)
add_tasks_btn.setStyleSheet(""" 

        QPushButton {
            color: white;
            background-color: #6D5AE6;
            border: none;
            border-radius: 18px;
            font-size: 23px;
            font-weight: bold;
        }

        QPushButton:hover {
                 background-color: #8170F0;        
        }

""")
add_tasks_btn.clicked.connect(open_tasks_dialog)

tasks_card_layout.addLayout(tasks_header)
tasks_header.addWidget(add_tasks_btn)

tasks_count = QLabel("0")

tasks_count.setStyleSheet(""" 
        
            color: #F8FAFC;
            font-size: 40px;
            font-weight: bold;
            background-color: transparent;
            border: none;

""")

tasks_card_layout.addWidget(tasks_count)

tasks_subtitle = QLabel("No tasks completed")
tasks_subtitle.setStyleSheet(""" 

        color: #AAB7CC;
        font-size: 14px;
        background-color: transparent;
        border: none;

""")

tasks_card_layout.addWidget(tasks_subtitle)
cards_row.addWidget(tasks_card)

weekly_card = QFrame()
weekly_card.setObjectName("weeklyCard")
weekly_card.setStyleSheet("""
      QFrame#weeklyCard {
            background-color: #172338;
            border: 1px solid #2B3A52;
            border-radius: 16px;
      }

""")
weekly_card.setFixedHeight(220)

weekly_layout = QVBoxLayout(weekly_card)
weekly_layout.setContentsMargins(20,15,20,15)
weekly_layout.setAlignment(Qt.AlignTop)

weekly_title = QLabel("WEEKLY PROGRESS")
weekly_title.setStyleSheet("""
      color: white;
      font-size: 18px;
      font-weight: bold;
      background-color: transparent;
      border: none;
""")

weekly_layout.addWidget(weekly_title)

chart_layout = QHBoxLayout()
chart_layout.addSpacing(35)

weekly_layout.addLayout(chart_layout)

days = ["MON","TUE","WED","THURS","FRI","SAT","SUN"]
weekly_bars = []

for day in days:
    day_layout =QVBoxLayout()


    progress_bar = QProgressBar()
    progress_bar.setOrientation(Qt.Vertical)
    progress_bar.setRange(0,100)
    progress_bar.setValue(0)
    progress_bar.setTextVisible(False)
    progress_bar.setFixedSize(30,110)
    progress_bar.setStyleSheet("""
      QProgressBar {
            background-color: #0B1220;
            border: none;
            border-radius: 6px;   
      }

      QProgressBar::chunk {
            background-color: #6D5AE6;
            border-radius: 6px;
      }
""")
    day_label = QLabel(day)
    day_label.setStyleSheet("""
            color: #94A3B8;
            font-size: 11px;
            background-color: transparent;
            border: none;
""")

    day_layout.addWidget(progress_bar,alignment=Qt.AlignHCenter)
    day_layout.addWidget(day_label,alignment=Qt.AlignHCenter)

    chart_layout.addLayout(day_layout)
    weekly_bars.append(progress_bar)

content_layout.addLayout(cards_row)

pending_card = QFrame()
pending_card.setObjectName("pendingCard")
pending_card.setFixedHeight(250)
pending_card.setStyleSheet(""" 
      QFrame#pendingCard {
            background-color: #172338;
            border: 1px solid #2B3A52;
            border-radius: 16px;
      }
""")

pending_layout = QVBoxLayout(pending_card)
pending_layout.setContentsMargins(20,15,20,15)
pending_layout.setAlignment(Qt.AlignTop)

pending_title = QLabel("PENDING TASKS")
pending_title.setStyleSheet("""
      color: white;
      font-size: 18px;
      font-weight: bold;
      background-color: transparent;
      border: none;
""")
pending_layout.addWidget(pending_title)
pending_list_layout = QVBoxLayout()
pending_list_layout.setSpacing(12)

pending_layout.addLayout(pending_list_layout)

def refresh_pending_tasks():


    while pending_list_layout.count():
        item = pending_list_layout.takeAt(0)

        if item.widget():
            item.widget().deleteLater()

    pending = [
        task_item for task_item in tasks
        if not task_item.get("completed", False)
    ]

    if not pending:
        empty_label = QLabel("No pending tasks. You're all caught up!")
        empty_label.setStyleSheet("""
            color: #94A3B8;
            font-size: 13px;
            background-color: transparent;
            border: none;
        """)
        pending_list_layout.addWidget(empty_label)
        return

    for task_item in pending[:3]:

        task_checkbox = QCheckBox(task_item["task"])

        task_checkbox.setStyleSheet("""
            QCheckBox {
                color: #CBD5E1;
                font-size: 14px;
                spacing: 10px;
                background-color: transparent;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #94A3B8;
                border-radius: 9px;
                background-color: transparent;
            }

            QCheckBox::indicator:checked {
                background-color: #6D5AE6;
                border: 2px solid #6D5AE6;
            }
        """)

        def complete_task(checked, selected_task=task_item):
            if checked:
                selected_task["completed"] = True

                if selected_task not in completed_tasks:
                    completed_tasks.append(selected_task)

                tasks_count.setText(str(len(completed_tasks)))
                refresh_pending_tasks()

        task_checkbox.toggled.connect(complete_task)

        pending_list_layout.addWidget(task_checkbox)
refresh_pending_tasks()
content_layout.addWidget(pending_card)

reminder_card = QFrame()
reminder_card.setObjectName("reminderCard")
reminder_card.setFixedHeight(190)
reminder_card.setStyleSheet(""" 
      QFrame#reminderCard {
            background-color: #172338;
            border: 1px solid #2B3A52;
            border-radius: 16px;
      }
""")

reminder_layout = QVBoxLayout(reminder_card)
reminder_layout.setContentsMargins(20,15,20,15)
reminder_layout.setSpacing(10)
reminder_layout.setAlignment(Qt.AlignTop)

reminder_title = QLabel("EXAM REMINDER")

reminder_title.setStyleSheet(""" 
      color: white;
      font-size: 18px;
      font-weight: bold;
      background-color: transparent;
      border: none;
""")

reminder_layout.addWidget(reminder_title)

reminder_subject = QLabel("No upcoming exams")
reminder_subject.setStyleSheet("""
    color: white;
    font-size: 22px;
    font-weight: bold;
    background: transparent;
    border: none;
""")
reminder_layout.addWidget(reminder_subject)

reminder_date = QLabel("Add an exam to see its date here")
reminder_date.setStyleSheet("""
    color: #94A3B8;
    font-size: 14px;
    background: transparent;
    border: none;
""")
reminder_layout.addWidget(reminder_date)

reminder_countdown = QLabel("Your next exam will appear here")
reminder_countdown.setStyleSheet("""
    color: #A78BFA;
    font-size: 14px;
    font-weight: bold;
    background: transparent;
    border: none;
""")
reminder_layout.addWidget(reminder_countdown)

content_layout.addWidget(reminder_card)
content_layout.addWidget(weekly_card)
content_layout.addStretch()

refresh_exam_reminder()

main_window.show()

sys.exit(app.exec())