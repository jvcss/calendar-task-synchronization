import streamlit as st

st.set_page_config(
    page_title="Automation of Calendar Sync",
    layout="wide",
)

# Initialize session state for slide index
if 'slide' not in st.session_state:
    st.session_state.slide = 0

# Define slides content
slides = [
    {
        "title": "Automation of Calendar Sync.",
        "author": "Tapir Lab.",
        "date": "December 2020",
        "content": None,
    },
    {
        "title": "Automation on Windows",
        "content": {
            "Steps": [
                "Click start and type **Task Scheduler** and run it.",
                "Go to **Action > Import Task…** and import `Synchronize.xml`.",
                "In the **Actions** tab, select the action and click Edit.",
                "Browse to your `run_main.vbs` and select it.",
                "Copy its full path into the **Start in (optional)** field.",
                "Click **OK** and run the task manually to verify.",
            ]
        }
    },
    {
        "title": "If Import Doesn’t Work",
        "content": {
            "Steps": [
                "Open Task Scheduler and choose **Create Task…**.",
                "On the **General** tab, name it and enable **Run with highest privileges**.",
                "On the **Triggers** tab, click **New…** and configure your schedule.",
                "On the **Actions** tab, click **New…** → **Start a Program**.",
                "Browse to `run_main.vbs` and set its folder in **Start in (optional)**.",
                "Adjust any **Conditions** or **Settings**, save, and test.",
                "For full docs see Microsoft’s Task Scheduler guide: [Microsoft Task Scheduler](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)",
            ]
        }
    },
    {
        "title": "Automation on Linux",
        "content": {
            "Steps": [
                "Install `crontab` if needed.",
                "Cd into the `automation_of_sync` folder.",
                "Update paths in `synchronization.sh` and `example_crontab.txt`.",
                "Import the example crontab (will overwrite):\n- `crontab example_crontab.txt`\n- Verify with `crontab -l`",
                "Grant execute permission if needed:\n```sudo chmod +x synchronization.sh```",
                "The default job runs `main.py` every 10 minutes and logs to `test.log`.",
            ]
        }
    }
]

# Navigation buttons
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("◀ Prev"):
        if st.session_state.slide > 0:
            st.session_state.slide -= 1
with col2:
    if st.button("Next ▶"):
        if st.session_state.slide < len(slides) - 1:
            st.session_state.slide += 1

# Render current slide
current = slides[st.session_state.slide]
st.title(current['title'])

# Display metadata if present
if 'author' in current:
    st.write(f"*Author:* {current['author']}")
if 'date' in current:
    st.write(f"*Date:* {current['date']}")

# Display content
content = current.get('content')
if content:
    for heading, items in content.items():
        st.subheader(heading)
        for idx, line in enumerate(items, start=1):
            # Support multi-line entries
            if '\n' in line:
                st.markdown(f"{idx}. " + line)
            else:
                st.markdown(f"{idx}. {line}")

# Footer navigation hint
st.markdown("---")
st.markdown("Use the buttons above or arrow keys to navigate through the slides.")

# Enable keyboard navigation via JavaScript hack
st.components.v1.html('''
<script>
document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') {
        document.querySelector('button[aria-label="◀ Prev"]').click();
    }
    if (e.key === 'ArrowRight') {
        document.querySelector('button[aria-label="Next ▶"]').click();
    }
});
</script>
''', height=0)
