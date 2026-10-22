"""Liste les tableaux de body.tex (étiquette et légende) et signale ceux qui contiennent des nombres saisis à la main."""
import re
from pathlib import Path

s = Path(__file__).resolve().parent.parent.joinpath("body.tex").read_text(encoding="utf-8")
for m in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", s, flags=re.S):
    bloc = m.group(0)
    lab = re.search(r"\\label\{(tab:[^}]*)\}", bloc)
    cap = re.search(r"\\caption\{(.*?)\}\s*\\label", bloc, flags=re.S)
    nb = len(re.findall(r"\d[\d,]*\d|\d", re.sub(r"\\[a-zA-Z]+|\$[^$]*\$", "", bloc.split("\\end{tabular}")[0])))
    print(f"{lab.group(1) if lab else '?':22s} chiffres={nb:4d} | {(cap.group(1) if cap else '')[:100]}")
