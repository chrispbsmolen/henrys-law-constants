"""Suggested InChIKeys for the species in 5.0.0 that have none.

Usage: python3 -I inchikey_suggestions.py <reportdir>      (needs RDKit; reads nothing online)

Writes <reportdir>/for_the_compiler/inchikey_suggestions.csv. The structures were
taken from PubChem (looked up on 9 November 2026 by the compound's own IUPAC
name, or by CAS RN where the name was not found) and are written out below as
SMILES. For each one RDKit recomputes the InChIKey and the CIP labels, and the
script stops if the labels do not match the stereo descriptors in the name.

The six species that are racemic diastereomers (triadimenol A and B, cis- and
trans-propiconazole, the two bromuconazole isomers) get no suggestion: a
standard InChIKey describes absolute configuration and cannot say "racemic,
relative configuration (R*,S*)", and the parent compounds in the table already
carry the stereo-free key (triadimenol, propiconazole, bromuconazole).
"""
import csv
import os
import sys

from rdkit import Chem, RDLogger
from rdkit.Chem import rdCIPLabeler, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

NO2 = "O[N+](=O)[O-]"
# species_id, name in the table, CAS RN, expected CIP labels, SMILES, where the structure came from
ROWS = [
    ("5943", "(2R,4S)-2,4-pentanediol dinitrate", "208252-05-5", "RS",
     "C[C@H](C[C@H](C)%s)%s" % (NO2, NO2), "PubChem CID 165359882 (by name; also by CAS RN)"),
    ("5944", "(2R,4R)-2,4-pentanediol dinitrate", "208252-04-4", "RR",
     "C[C@H](C[C@@H](C)%s)%s" % (NO2, NO2),
     "PubChem CID 165359880 (by name) is the hydrate; with the water removed it is CID 165359881"),
    ("5949", "(1R,2S)-1,2-cyclohexanediol dinitrate", "32342-28-2", "RS",
     "C1CC[C@@H]([C@@H](C1)%s)%s" % (NO2, NO2), "PubChem CID 129719149 (by name; also by CAS RN)"),
    ("5950", "(1R,2R)-1,2-cyclohexanediol dinitrate", "32342-29-3", "RR",
     "C1CC[C@H]([C@@H](C1)%s)%s" % (NO2, NO2), "PubChem CID 129719166 (by name; also by CAS RN)"),
    ("5951", "(1R,3S)-1,3-cyclohexanediol dinitrate", "170994-36-2", "RS",
     "C1C[C@H](C[C@H](C1)%s)%s" % (NO2, NO2), "PubChem CID 129719164 (by CAS RN; name not found)"),
    ("5952", "(1R,3R)-1,3-cyclohexanediol dinitrate", "170994-41-9", "RR",
     "C1C[C@H](C[C@@H](C1)%s)%s" % (NO2, NO2),
     "PubChem CID 177409255; the CAS RN points to CID 129719154, which is (1S,3S)"),
    ("5954", "(1R,2R)-1,2-cycloheptanediol dinitrate", "208252-06-6", "RR",
     "C1CC[C@H]([C@@H](CC1)%s)%s" % (NO2, NO2), "PubChem CID 165359883 (by name; also by CAS RN)"),
]
NONE = [
    ("8624", "triadimenol B", "82200-72-4"),
    ("8625", "triadimenol A", "89482-17-7"),
    ("8634", "cis-propiconazole", "112721-87-6"),
    ("8635", "trans-propiconazole", "120523-07-1"),
    ("9249", "(±)-(2R^*,4S^*)-bromuconazole", "114544-80-8"),
    ("9250", "(±)-(2R^*,4R^*)-bromuconazole", "114544-81-9"),
]
MESO = {"5943", "5949", "5951"}


def main():
    dest = os.path.join(sys.argv[1], "for_the_compiler")
    os.makedirs(dest, exist_ok=True)
    out = []
    for sid, name, cas, cip, smi, src in ROWS:
        m = Chem.MolFromSmiles(smi)
        rdCIPLabeler.AssignCIPLabels(m)
        got = "".join(sorted(a.GetProp("_CIPCode") for a in m.GetAtoms() if a.HasProp("_CIPCode")))
        if got != "".join(sorted(cip)):
            sys.exit("%s: CIP labels %s do not match the name (%s)" % (name, got, cip))
        note = ("meso compound, so this key is the only one" if sid in MESO else
                "chiral: this key is the enantiomer named; if the measured compound was the racemic "
                "trans isomer, the stereo-free key or a note may fit better")
        out.append([sid, name, cas, Chem.MolToInchiKey(m), rdMolDescriptors.CalcMolFormula(m), src, note])
    for sid, name, cas in NONE:
        out.append([sid, name, cas, "", "", "",
                    "racemic diastereomer: no standard InChIKey for relative configuration; "
                    "the parent compound already has the stereo-free key"])
    with open(os.path.join(dest, "inchikey_suggestions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["species_id", "name", "casrn", "suggested_inchikey", "formula", "structure_source", "note"])
        w.writerows(out)
    for r in out:
        print(r[0], r[3] or "-", r[1])


if __name__ == "__main__":
    main()
