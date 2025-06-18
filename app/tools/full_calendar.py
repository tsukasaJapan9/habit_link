import json

import streamlit.components.v1 as components

# ▼運動履歴：運動した日と内容（バックエンドなどから取得したデータ）
exercise_log = [
  {"title": "ウォーキング", "date": "2025-04-25"},
  {"title": "ジョギング", "date": "2025-04-26"},
  {"title": "ヨガ", "date": "2025-04-28"},
]

# JSON文字列化してHTMLに埋め込む
events_json = json.dumps(exercise_log)

# ▼カレンダー描画（FullCalendar.js）
components.html(
  f"""
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css' rel='stylesheet' />
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'></script>
<div id='calendar'></div>
<script>
  document.addEventListener('DOMContentLoaded', function() {{
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {{
      initialView: 'dayGridMonth',
      locale: 'ja',
      height: 500,
      events: {events_json}
    }});
    calendar.render();
  }});
</script>
""",
  height=550,
)


components.html(
  f"""
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css' rel='stylesheet' />
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'></script>
<div id='calendar'></div>
<script>
  document.addEventListener('DOMContentLoaded', function() {{
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {{
      initialView: 'dayGridMonth',
      locale: 'ja',
      height: 500,
      events: {events_json}
    }});
    calendar.render();
  }});
</script>
""",
  height=550,
)
