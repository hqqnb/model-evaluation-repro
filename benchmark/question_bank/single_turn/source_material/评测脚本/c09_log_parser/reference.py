import re


TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$")
LEVELS = {"INFO", "WARN", "ERROR"}


def parse_log(data: str):
    records = []
    errors = []
    i, line, n = 0, 1, len(data)

    while i < n:
        if data[i] == "\n":
            line += 1
            i += 1
            continue
        if data[i] == "\r":
            i += 1
            continue
        start_line = line

        m = re.match(r"\[([^\]]+)\] LVL=([A-Z]+) NODE=(\S+) MSG=\"", data[i:])
        if not m:
            while i < n and data[i] != "\n":
                i += 1
            errors.append((start_line, "invalid header"))
            continue

        ts, lv, node = m.groups()
        i += m.end()
        msg = []
        escaped = False
        closed = False
        while i < n:
            c = data[i]
            if escaped:
                if c == '"':
                    msg.append('"')
                elif c == "\\":
                    msg.append("\\")
                elif c == "n":
                    msg.append("\n")
                else:
                    msg.append(c)
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                closed = True
                i += 1
                break
            else:
                if c == "\n":
                    line += 1
                msg.append(c)
            i += 1

        if not closed:
            errors.append((start_line, "unclosed quote"))
            continue

        while i < n and data[i] in " \t":
            i += 1
        if i < n and data[i] not in "\r\n":
            while i < n and data[i] != "\n":
                i += 1
            errors.append((start_line, "trailing content"))
            continue

        if not TS_RE.fullmatch(ts):
            errors.append((start_line, "bad timestamp"))
            continue
        if lv not in LEVELS:
            errors.append((start_line, "invalid level"))
            continue
        records.append((ts, lv, node, "".join(msg)))

    return records, errors
