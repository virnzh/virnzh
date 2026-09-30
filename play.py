#!/usr/bin/env python3
"""Ular Tangga untuk README profil GitHub.

Dijalankan oleh GitHub Actions setiap ada issue "ular-tangga" baru.
  python game/play.py          -> lempar dadu untuk $PLAYER
  python game/play.py --init   -> hanya menggambar ulang papan
"""
import json
import os
import random
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "game" / "state.json"
README = ROOT / "README.md"
START, END = "<!--GAME_START-->", "<!--GAME_END-->"

SNAKES = {99: 54, 95: 75, 92: 73, 74: 53, 64: 60, 62: 19, 49: 11, 46: 25, 16: 6}
LADDERS = {2: 38, 7: 14, 8: 31, 15: 26, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 78: 98, 87: 94}
TOKENS = ["🔵", "🟣", "🟢", "🟠", "🔴", "🟡", "🟤", "⚪"]


def load():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"players": {}, "wins": {}, "rounds": 0, "log": []}


def save(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def move(state, player):
    pos = state["players"].get(player, 0)
    dice = random.randint(1, 6)
    new = pos + dice
    lines = [f"🎲 **@{player}** melempar dadu dan mendapat **{dice}**."]
    mark = ""

    if new > 100:
        lines.append(f"Butuh angka yang pas untuk sampai ke 100, jadi tetap di kotak {pos}.")
        new = pos
    else:
        lines.append(f"Maju dari kotak {pos} ke kotak {new}.")
        if new in SNAKES:
            lines.append(f"🐍 Ups, ada ular! Turun ke kotak **{SNAKES[new]}**.")
            new, mark = SNAKES[new], "🐍"
        elif new in LADDERS:
            lines.append(f"🪜 Asyik, ada tangga! Naik ke kotak **{LADDERS[new]}**.")
            new, mark = LADDERS[new], "🪜"

    entry = f"@{player}: 🎲{dice} → kotak {new} {mark}".strip()
    state["log"] = ([entry] + state.get("log", []))[:5]

    if new == 100:
        state["wins"][player] = state["wins"].get(player, 0) + 1
        state["rounds"] += 1
        state["players"] = {}
        state["log"].insert(0, f"🏆 @{player} MENANG! Papan direset.")
        lines.append(f"🏆 **Selamat @{player}, kamu menang!** Papan direset untuk ronde baru.")
    else:
        state["players"][player] = new
        lines.append(f"Posisimu sekarang: kotak **{new}**.")
    return "\n\n".join(lines)


def cell(n, occupied):
    if n in SNAKES:
        label = f"🐍 {n}<br>↓ {SNAKES[n]}"
    elif n in LADDERS:
        label = f"🪜 {n}<br>↑ {LADDERS[n]}"
    elif n == 100:
        label = "🏁 100"
    else:
        label = str(n)
    tokens = "".join(occupied.get(n, []))
    return f"**{label}**<br>{tokens}" if tokens else label


def render(state, repo):
    players = state["players"]
    occupied = {}
    for i, (name, pos) in enumerate(players.items()):
        occupied.setdefault(pos, []).append(TOKENS[i % len(TOKENS)])

    rows = ["| " + " | ".join("ABCDEFGHIJ") + " |", "|" + ":---:|" * 10]
    for r in range(9, -1, -1):
        nums = list(range(r * 10 + 1, r * 10 + 11))
        if r % 2 == 1:
            nums.reverse()
        rows.append("| " + " | ".join(cell(n, occupied) for n in nums) + " |")

    link = (
        f"https://github.com/{repo}/issues/new?title="
        + quote("ular-tangga: lempar dadu")
        + "&body="
        + quote("Klik tombol hijau 'Submit new issue' untuk melempar dadu! 🎲")
    )

    if players:
        plist = "\n".join(
            f"- {TOKENS[i % len(TOKENS)]} **@{n}** — "
            + (f"kotak {p}" if p else "di garis start")
            for i, (n, p) in enumerate(players.items())
        )
    else:
        plist = "_Belum ada pemain di ronde ini. Jadilah yang pertama!_"

    wins = sorted(state["wins"].items(), key=lambda kv: -kv[1])[:5]
    hall = (
        "\n".join(f"{i}. **@{n}** — {w}x menang" for i, (n, w) in enumerate(wins, 1))
        if wins
        else "_Belum ada pemenang._"
    )
    log = "\n".join(f"- {e}" for e in state.get("log", [])) or "_Belum ada langkah._"

    return f"""{START}
<div align="center">

### 🎲 Ular Tangga Bareng Pengunjung

Semua orang yang mampir ke profil ini bisa ikut main di papan yang sama!<br>
Klik tombol, lalu tekan **Submit new issue**. Dalam ±1 menit dadumu dilempar dan papan ini otomatis diperbarui.

## [🎲 LEMPAR DADU SEKARANG]({link})

</div>

{chr(10).join(rows)}

🐍 = ular (turun) &nbsp; 🪜 = tangga (naik) &nbsp; 🏁 = finis &nbsp; | &nbsp; Ronde ke-{state["rounds"] + 1}

**Pemain ronde ini**

{plist}

**Langkah terakhir**

{log}

**🏆 Hall of Fame**

{hall}
{END}"""


def update_readme(state, repo):
    text = README.read_text(encoding="utf-8")
    block = render(state, repo)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        sys.exit("Penanda <!--GAME_START--> dan <!--GAME_END--> tidak ditemukan di README.md")
    README.write_text(pattern.sub(lambda _: block, text), encoding="utf-8")


def main():
    repo = os.environ.get("REPO", "USERNAME/USERNAME")
    state = load()
    if "--init" not in sys.argv:
        player = os.environ["PLAYER"]
        message = move(state, player)
        message += f"\n\nLihat papan terbaru di https://github.com/{repo.split('/')[0]} 💙"
        Path(os.environ.get("MESSAGE_FILE", "/tmp/msg.md")).write_text(message, encoding="utf-8")
    save(state)
    update_readme(state, repo)


if __name__ == "__main__":
    main()
