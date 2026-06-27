import json
import os
import re
import shutil

from utils import AGY_DIR


def clean_conversations(json_output=False):
    import sys
    history_file = os.path.join(AGY_DIR, "history.jsonl")
    active_uuids = set()
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        conversation_id = data.get("conversationId")
                        if conversation_id:
                            active_uuids.add(conversation_id)
                    except Exception:
                        pass
        except Exception as exc:
            print(f"❌ Error reading history.jsonl: {exc}", file=sys.stderr)
            return

    conversations_dir = os.path.join(AGY_DIR, "conversations")
    brain_dir = os.path.join(AGY_DIR, "brain")
    cleaned_count = 0
    total_saved_bytes = 0

    if os.path.exists(conversations_dir):
        for filename in os.listdir(conversations_dir):
            if not (filename.endswith(".db") or filename.endswith(".pb")):
                continue
            conversation_id = filename.split(".")[0]
            if conversation_id in active_uuids:
                continue
            path = os.path.join(conversations_dir, filename)
            try:
                total_saved_bytes += os.path.getsize(path)
                os.remove(path)
                cleaned_count += 1
            except Exception as exc:
                print(f"⚠️ Failed to remove {filename}: {exc}", file=sys.stderr)

    if os.path.exists(brain_dir):
        for dirname in os.listdir(brain_dir):
            if not re.match(r"^[0-9a-fA-F-]{36}$", dirname):
                continue
            if dirname in active_uuids:
                continue
            path = os.path.join(brain_dir, dirname)
            try:
                total_saved_bytes += sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(path)
                    for filename in filenames
                )
                shutil.rmtree(path)
            except Exception as exc:
                print(f"⚠️ Failed to remove directory {dirname}: {exc}", file=sys.stderr)

    mb_saved = total_saved_bytes / (1024 * 1024)
    if json_output:
        print(json.dumps({
            "status": "success",
            "cleaned_count": cleaned_count,
            "bytes_saved": total_saved_bytes,
            "mb_saved": round(mb_saved, 2)
        }))
    else:
        print(f"🧹 Cleaned up {cleaned_count} automated/orphaned sessions.")
        print(f"💾 Saved {mb_saved:.2f} MB of disk space.")


def _history_entries(history_file):
    entries = []
    try:
        with open(history_file, "r") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("conversationId"):
                        entries.append(data)
                except Exception:
                    pass
    except Exception as exc:
        print(f"❌ Error reading history.jsonl: {exc}")
        return None
    return entries


def _print_conversations(conversations):
    print("\n💬 Available Conversations:")
    print("┌─────┬──────────────────────────────────────┬──────────────────────────────────────────┐")
    print("│ IDX │ CONVERSATION ID                      │ LATEST PROMPT                            │")
    print("├─────┼──────────────────────────────────────┼──────────────────────────────────────────┤")
    for index, conversation in enumerate(conversations):
        conversation_id = conversation["conversationId"]
        display = conversation.get("display", "").replace("\n", " ")
        if len(display) > 40:
            display = display[:37] + "..."
        idx_str = f"{index + 1}".center(5)
        display_padded = display.ljust(40)[:40]
        print(f"│{idx_str}│ {conversation_id} │ {display_padded} │")
    print("└─────┴──────────────────────────────────────┴──────────────────────────────────────────┘")
    print("To delete, run: agy delete <idx> or agy delete <conversation_id>")


def _select_conversation(conversations, target):
    if target.isdigit():
        index = int(target) - 1
        if 0 <= index < len(conversations):
            return conversations[index]["conversationId"]
        print(f"❌ Index {target} out of range (1 to {len(conversations)}).")
        return None

    if re.match(r"^[0-9a-fA-F-]{36}$", target):
        return target

    matches = [
        conversation
        for conversation in conversations
        if target.lower() in conversation.get("display", "").lower()
    ]
    if not matches:
        print(f"❌ No conversation found matching: '{target}'")
        return None
    if len(matches) > 1:
        print(f"⚠️ Multiple conversations matched '{target}':")
        for match in matches:
            print(f"  {match['conversationId']} - {match.get('display')}")
        return None
    return matches[0]["conversationId"]


def _remove_conversation_files(conversation_id):
    deleted_files = 0
    conversations_dir = os.path.join(AGY_DIR, "conversations")
    brain_dir = os.path.join(AGY_DIR, "brain")

    for extension in [".db", ".pb"]:
        path = os.path.join(conversations_dir, f"{conversation_id}{extension}")
        if os.path.exists(path):
            try:
                os.remove(path)
                deleted_files += 1
            except Exception as exc:
                print(f"⚠️ Failed to delete file {path}: {exc}")

    path = os.path.join(brain_dir, conversation_id)
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            deleted_files += 1
        except Exception as exc:
            print(f"⚠️ Failed to delete directory {path}: {exc}")

    return deleted_files


def _remove_history_entry(history_file, conversation_id):
    try:
        new_lines = []
        with open(history_file, "r") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("conversationId") != conversation_id:
                        new_lines.append(line)
                except Exception:
                    new_lines.append(line)
        with open(history_file, "w") as handle:
            handle.writelines(new_lines)
    except Exception as exc:
        print(f"⚠️ Failed to update history.jsonl: {exc}")


def delete_conversation(target=None):
    history_file = os.path.join(AGY_DIR, "history.jsonl")
    if not os.path.exists(history_file):
        print("❌ history.jsonl not found.")
        return

    history_entries = _history_entries(history_file)
    if history_entries is None:
        return
    if not history_entries:
        print("ℹ️ No conversations found in history.")
        return

    unique_conversations = {}
    for entry in history_entries:
        unique_conversations[entry["conversationId"]] = entry

    sorted_conversations = sorted(unique_conversations.values(), key=lambda item: item.get("timestamp", 0))
    if target is None:
        _print_conversations(sorted_conversations)
        return

    selected_id = _select_conversation(sorted_conversations, target)
    if not selected_id:
        return

    _remove_conversation_files(selected_id)
    _remove_history_entry(history_file, selected_id)
    print(f"🗑️ Successfully deleted conversation {selected_id}.")
