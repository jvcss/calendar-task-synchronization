import streamlit as st
import subprocess

st.set_page_config(page_title="Automation of Calendar Sync", layout="wide")

# Define tab structure
tabs = st.tabs(["Intro", "Windows Automation", "Linux Automation", "Cron Status"])

# Tab 1: Introduction
with tabs[0]:
    st.header("Automation of Calendar Sync")
    st.markdown("""
    - **Author:** Tapir Lab
    - **Date:** December 2020

    Welcome to the Automation of Calendar Synchronization tutorial. Navigate through the tabs to proceed.
    """)

# Tab 2: Windows Automation
with tabs[1]:
    st.header("Automation on Windows")
    st.markdown("""
    ### Steps:
    1. Open **Task Scheduler** from Start Menu.
    2. Select **Action > Import Task** and import `Synchronize.xml`.
    3. In the **Actions** tab, select the listed action, click **Edit**.
    4. Browse and select `run_main.vbs`.
    5. Copy the full path of `run_main.vbs` into **Start in (optional)**.
    6. Click **OK** and verify by running the task manually.

    ### If Import Doesn't Work
    - Create task manually:
        1. Open **Task Scheduler** > **Action > Create Task**.
        2. In **General**, name your task and enable **Run with highest privileges**.
        3. In **Triggers**, set your schedule.
        4. In **Actions**, select **Start a Program** and choose `run_main.vbs`.
        5. Adjust any **Conditions** or **Settings** and save.

    [Microsoft Task Scheduler Documentation](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)
    """)

# Tab 3: Linux Automation
with tabs[2]:
    st.header("Automation on Linux with Cron")
    st.markdown("""
    ### Steps:
    1. Install cron if necessary:
    ```bash
    sudo apt install cron
    ```
    2. Navigate to your automation folder.
    3. Update paths in `synchronization.sh` and `example_crontab.txt`.
    4. Import your crontab:
    ```bash
    crontab example_crontab.txt
    ```
    5. Verify crontab:
    ```bash
    crontab -l
    ```
    6. Make sure the script is executable:
    ```bash
    sudo chmod +x synchronization.sh
    ```

    **Cron Syntax:**
    ```
    * * * * * /path/to/script.sh
    - - - - -
    | | | | |
    | | | | +----- Day of the week (0-6) (Sunday=0)
    | | | +------- Month (1-12)
    | | +--------- Day of the month (1-31)
    | +----------- Hour (0-23)
    +------------- Minute (0-59)
    ```
    """)

# Tab 4: Cron Status - Live Monitoring
with tabs[3]:
    st.header("Current Cron Job Status")

    st.subheader("Active Cron Jobs")
    cron_list = subprocess.getoutput("crontab -l")
    st.code(cron_list, language="bash")

    st.subheader("Cron Service Status")
    cron_status = subprocess.getoutput("systemctl status cron")
    st.code(cron_status, language="bash")

    st.subheader("Recent Cron Logs")
    cron_logs = subprocess.getoutput("grep CRON /var/log/syslog | tail -n 10")
    st.code(cron_logs, language="bash")
