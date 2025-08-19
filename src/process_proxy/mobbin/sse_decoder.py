import json
import re
from typing import Any

def parse_sse_response(response_text: str) -> list[dict[str, Any]]:

    events = []

    # Разбиваем на строки
    lines = response_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Ищем паттерн "число:JSON"
        match = re.match(r'^(\d+):(.+)$', line)
        if match:
            event_id = int(match.group(1))
            json_data = match.group(2)

            # Парсим JSON
            try:
                parsed_data = json.loads(json_data)

                event_info = {
                    'id': event_id,
                    'data': parsed_data,
                    'raw': line
                }

                events.append(event_info)


            except json.JSONDecodeError:
                pass

    return events
