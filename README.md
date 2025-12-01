# RoBoCopy-Manager-For-Files-only-
A GUI-based fast file copy tool for Files only

📦 RoBoCopy Manager

A fast, lightweight, and user-friendly GUI-based file copy tool powered by Windows Robocopy.
Designed to simplify multi-file copying with speed, logs, and a clean interface.

🚀 Features

✔ Select multiple source files (must be in same folder)

✔ Destination folder auto-detection

✔ Fast copy preset using:"/E /MT:32 /R:1 /W:1"

✔ Real-time Robocopy output display

✔ Auto log saving in %USERPROFILE%/.robocopy_gui/logs

✔ "Preview Command" button

✔ Stop running process

✔ Clean Tkinter-based GUI

📂 Project Structure

RoBoCopy-Manager/

│

├── src/

│         └── RoBoCopy Manager.py

├── LICENSE

└── README.md

🛠️ Source Code

Main GUI application written in Python (Tkinter):

➡ src/RoBoCopy Manager.py

This script builds the Robocopy command, runs subprocess, handles logs, UI events, file selection, etc.

📘 How It Works

User selects multiple source files

Application extracts the parent folder

RoBoCopy Manager copies only selected filenames to destination

Logs are stored automatically

Interface shows real-time output


💡 Why This Tool Exists

RoBoCopy Manager is powerful but easy to use for normal users.
This tool provides a clean interface with safe defaults, making fast file copying easy for everyone.

👤 Author

Manoj Kumar (MK)

Feel free to contribute, report issues, or suggest features.

⭐ Support

If you like this project, consider ⭐ starring the repository on GitHub!
