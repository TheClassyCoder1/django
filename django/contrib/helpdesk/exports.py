import os
import re


def save_transcript(export_dir, ticket_info, content):
    name = ticket_info.get("title", None) or "ticket"
    name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    name = re.sub(r"[-\s]+", "-", name)
    fname = "{}-{}.txt".format(name, ticket_info["id"])
    file_path = os.path.join(export_dir, fname)
    with open(file_path, "wb") as f:
        f.write(content)
