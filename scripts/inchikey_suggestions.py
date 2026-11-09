"""Suggested InChIKeys for the 13 species in 5.0.0 that have none.

Usage: python3 -I inchikey_suggestions.py <reportdir>      (needs RDKit; reads nothing online)

Writes <reportdir>/for_the_compiler/inchikey_suggestions.csv. Each structure is
written out below as SMILES with the PubChem record it was taken from (looked up
on 9 November 2026). RDKit recomputes every InChIKey and the CIP labels, and the
script stops if the labels do not fit the name in the table:
  - names with explicit descriptors (the dinitrates): the labels must be exactly
    those of the name;
  - names with relative descriptors or A/B, cis/trans (the azoles): the two
    stereocentres must be alike (R,R or S,S) or unlike (R,S) as the name says,
    following the PubChem record's own synonyms.

Three species are meso compounds and have a single key. The other ten are
chiral and were most likely measured as racemates; a standard InChIKey states
an absolute configuration and cannot say "racemic", so the key given is that of
one enantiomer, standing in for the pair (Henry's law constants of two
enantiomers are equal). The stereo-free key would not do: it is the same for
the cis and trans isomer of each compound and is already used by the parent
compounds (triadimenol, propiconazole, bromuconazole) in the table.
"""
import csv
import os
import sys

from rdkit import Chem, RDLogger
from rdkit.Chem import rdCIPLabeler, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

NO2 = "O[N+](=O)[O-]"
# species_id, name in the table, CAS RN in the table, stereo check, SMILES, source, note
ROWS = [
    ("5943", "(2R,4S)-2,4-pentanediol dinitrate", "208252-05-5", "exact:RS",
     "C[C@H](C[C@H](C)%s)%s" % (NO2, NO2), "PubChem CID 165359882 (by name and by CAS RN)",
     "meso compound: one key"),
    ("5944", "(2R,4R)-2,4-pentanediol dinitrate", "208252-04-4", "exact:RR",
     "C[C@H](C[C@@H](C)%s)%s" % (NO2, NO2), "PubChem CID 165359881",
     "(R,R) enantiomer as named, standing in for the racemic trans isomer. PubChem's records for the "
     "name and for the CAS RN (CID 165359880) are a hydrate."),
    ("5949", "(1R,2S)-1,2-cyclohexanediol dinitrate", "32342-28-2", "exact:RS",
     "C1CC[C@@H]([C@@H](C1)%s)%s" % (NO2, NO2), "PubChem CID 129719149 (by name and by CAS RN)",
     "meso compound: one key"),
    ("5950", "(1R,2R)-1,2-cyclohexanediol dinitrate", "32342-29-3", "exact:RR",
     "C1CC[C@H]([C@@H](C1)%s)%s" % (NO2, NO2), "PubChem CID 129719166 (by name and by CAS RN)",
     "(R,R) enantiomer as named, standing in for the racemic trans isomer"),
    ("5951", "(1R,3S)-1,3-cyclohexanediol dinitrate", "170994-36-2", "exact:RS",
     "C1C[C@H](C[C@H](C1)%s)%s" % (NO2, NO2), "PubChem CID 129719164 (by CAS RN; the name is not found)",
     "meso compound: one key"),
    ("5952", "(1R,3R)-1,3-cyclohexanediol dinitrate", "170994-41-9", "exact:RR",
     "C1C[C@H](C[C@@H](C1)%s)%s" % (NO2, NO2),
     "PubChem CID 177409255 (found by the computed key; the name is not found)",
     "(R,R) enantiomer as named, standing in for the racemic trans isomer. PubChem maps the CAS RN "
     "to the (S,S) enantiomer, CID 129719154."),
    ("5954", "(1R,2R)-1,2-cycloheptanediol dinitrate", "208252-06-6", "exact:RR",
     "C1CC[C@H]([C@@H](CC1)%s)%s" % (NO2, NO2), "PubChem CID 165359883 (by name and by CAS RN)",
     "(R,R) enantiomer as named, standing in for the racemic trans isomer"),
    ("8624", "triadimenol B", "82200-72-4", "alike",
     "CC(C)(C)[C@@H]([C@@H](N1C=NC=N1)OC2=CC=C(C=C2)Cl)O",
     "PubChem CID 93469 (synonyms: Triadimenol B, (alphaR,betaR)-rel-)",
     "one enantiomer standing in for the racemate (1RS,2RS). Please check the CAS RN: PubChem lists "
     "82200-72-4 as a synonym of triadimenol A (CID 92416), and gives 70585-37-4 for B."),
    ("8625", "triadimenol A", "89482-17-7", "unlike",
     "CC(C)(C)[C@H]([C@@H](N1C=NC=N1)OC2=CC=C(C=C2)Cl)O",
     "PubChem CID 92416 (synonyms: Triadimenol A, (1RS,2SR)-Triadimenol; also lists 89482-17-7)",
     "one enantiomer standing in for the racemate (1RS,2SR)"),
    ("8634", "cis-propiconazole", "112721-87-6", "unlike",
     "CCC[C@H]1CO[C@](O1)(CN2C=NC=N2)C3=C(C=C(C=C3)Cl)Cl",
     "PubChem CID 679162 (synonym: cis-propiconazole)",
     "one enantiomer standing in for the racemate. PubChem does not know CAS RN 112721-87-6; it gives "
     "116498-44-3 for this record."),
    ("8635", "trans-propiconazole", "120523-07-1", "alike",
     "CCC[C@@H]1CO[C@](O1)(CN2C=NC=N2)C3=C(C=C(C=C3)Cl)Cl",
     "PubChem CID 679163 (synonym: trans-propiconazole; also lists 120523-07-1)",
     "one enantiomer standing in for the racemate"),
    ("9249", "(±)-(2R^*,4S^*)-bromuconazole", "114544-80-8", "unlike",
     "C1[C@H](CO[C@]1(CN2C=NC=N2)C3=C(C=C(C=C3)Cl)Cl)Br",
     "PubChem CID 16760138 (by CAS RN; synonym rel-(2R,4S))",
     "one enantiomer, (2S,4R), standing in for the racemate"),
    ("9250", "(±)-(2R^*,4R^*)-bromuconazole", "114544-81-9", "alike",
     "C1[C@@H](CO[C@]1(CN2C=NC=N2)C3=C(C=C(C=C3)Cl)Cl)Br",
     "PubChem CID 16760149 (by CAS RN; synonym rel-(2R,4R))",
     "one enantiomer, (2S,4S), standing in for the racemate"),
]


def main():
    dest = os.path.join(sys.argv[1], "for_the_compiler")
    os.makedirs(dest, exist_ok=True)
    out = []
    for sid, name, cas, check, smi, src, note in ROWS:
        m = Chem.MolFromSmiles(smi)
        rdCIPLabeler.AssignCIPLabels(m)
        labels = sorted(a.GetProp("_CIPCode") for a in m.GetAtoms() if a.HasProp("_CIPCode"))
        if len(labels) != 2:
            sys.exit("%s: expected two stereocentres, found %r" % (name, labels))
        alike = labels[0] == labels[1]
        ok = ("".join(labels) == "".join(sorted(check[6:])) if check.startswith("exact:")
              else alike == (check == "alike"))
        if not ok:
            sys.exit("%s: CIP labels %r do not fit %s" % (name, labels, check))
        kind = "meso" if note.startswith("meso") else "one enantiomer for the racemate"
        out.append([sid, name, cas, Chem.MolToInchiKey(m), kind, rdMolDescriptors.CalcMolFormula(m), src, note])
    with open(os.path.join(dest, "inchikey_suggestions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["species_id", "name", "casrn", "suggested_inchikey", "kind", "formula", "structure_source", "note"])
        w.writerows(out)
    for r in out:
        print(r[0], r[3], r[4], r[1])


if __name__ == "__main__":
    main()
