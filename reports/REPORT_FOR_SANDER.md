# Points for the compiler: henry-5.0.0.sql

Prepared by Christopher Smolen while converting the published SQL dump of the compilation (version 5.0.0) into tidy tables. Nothing listed here was changed in the converted tables; every item is reported as found. Row ids are those PostgreSQL assigns when the dump is loaded into an empty database (henry_id is the id that CURRVAL('henry_id_seq') returns). The full machine-readable list is `reports/inconsistencies.csv`.

The dump itself is in good order: all 104054 INSERT statements load, every name lookup except three resolves to exactly one row, no note link collides, and the values agree one for one with output/HscpSI.f90 and output/Hscp.f90 in the supplement.

## 1. References to the key 'this' (3 rows)

These henry rows look up `bibtexkey='this'`, which has no row in the literature table, so literature_id is NULL after loading. The Fortran files show `ref: this` for the same rows (presumably 'this work').

- henry 422: bibtexkey 'this' has no literature row; species 'dichlorine monoxide', H='3.4&times;10<sup>&#8722;2</sup>', mindHR='5900', type R
- henry 423: bibtexkey 'this' has no literature row; species 'dichlorine monoxide', H='7.6&times;10<sup>&#8722;2</sup>', mindHR='5600', type R
- henry 517: bibtexkey 'this' has no literature row; species 'bromine chloride', H='1.1&times;10<sup>&#8722;2</sup>', mindHR='', type T

## 2. Rows for the same species and reference that cannot be told apart

22 species/reference pairs have two or more rows that are identical in value, temperature dependence, type and notes:

- henry 34;35;36: species 'oxygen', reference 2375: 3 rows, of which some are identical in value, mindHR, type and notes
- henry 6813;6814;6819;6820: species '1-hexyne', reference 3586: 4 rows, of which some are identical in value, mindHR, type and notes
- henry 7132;7133: species 'benzene', reference 2375: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 7921;7922;7927;7928: species '1-ethyl-4-methylbenzene', reference 3586: 4 rows, of which some are identical in value, mindHR, type and notes
- henry 8120;8121;8133;8134: species '1-methyl-4-(1-methylethyl)-benzene', reference 3586: 4 rows, of which some are identical in value, mindHR, type and notes
- henry 11221;11222: species '3-methyl-3-octanol', reference 3579: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 11478;11479: species '3-ethyl-2,4-dimethyl-3-pentanol', reference 3579: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 11822;11823: species '2-methyl-3-(1-methylethyl)-3-hexanol', reference 3579: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 2617;2618: species '3-ethyl-2,2-dimethylhexane', reference 2521: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 23351;23352: species '2-methoxy-2-methylbutane', reference 3579: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 25097;25098: species 'vanillin', reference 3682: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 26084;26085: species '2-methylbenzenamine', reference 636: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 27161;27162: species 'benzenenitrile', reference 636: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 27678;27679;27682;27683: species 'fenoxycarb', reference 3586: 4 rows, of which some are identical in value, mindHR, type and notes
- henry 31664;31665;31666;31667;31668;31669;31670;31671: species '2-nitrotoluene', reference 2995: 8 rows, of which some are identical in value, mindHR, type and notes
- henry 31784;31785;31786;31787;31788;31789;31790;31791: species '1-methyl-2,3-dinitrobenzene', reference 2995: 8 rows, of which some are identical in value, mindHR, type and notes
- henry 32968;32969;32970;32971;32972;32973;32974;32975: species 'pentadecafluorooctanoic acid', reference 2995: 8 rows, of which some are identical in value, mindHR, type and notes
- henry 34219;34220;34222;34223: species '1,1-dichloropropane', reference 3586: 4 rows, of which some are identical in value, mindHR, type and notes
- henry 695;696: species 'argon', reference 2375: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 40641;40642: species '4-chloronitrobenzene', reference 2521: 2 rows, of which some are identical in value, mindHR, type and notes
- henry 41112;41113;41114;41115: species 'chlozolinate', reference 3586: 4 rows, of which some are identical in value, mindHR, type and notes
- henry 1064;1065: species '2-methylpropane', reference 2535: 2 rows, of which some are identical in value, mindHR, type and notes

65 further pairs have rows with different values but the same type and the same notes, so a reader cannot tell which value belongs to which condition or method (7049 more pairs differ in type or notes, which explains them; those are listed in the CSV with severity info):

- henry 34;35;36: species 'oxygen', reference 2375: values 1.2&times;10<sup>&#8722;5</sup>|1600|V, 1.2&times;10<sup>&#8722;5</sup>|1600|V, 1.3&times;10<sup>&#8722;5</sup>|1500|V; notes identical for all rows; same type
- henry 46392;46393: species 'dimethylmercury', reference 2171: values 1.5&times;10<sup>&#8722;3</sup>|-|?, 1.3&times;10<sup>&#8722;3</sup>|2700|?; notes identical for all rows; same type
- henry 6391;6392: species '2-methyl-1,3-butadiene', reference 2440: values 1.1&times;10<sup>&#8722;4</sup>|-|?, 1.3&times;10<sup>&#8722;4</sup>|-|?; notes identical for all rows; same type
- henry 6386;6387: species '2-methyl-1,3-butadiene', reference 3731: values 1.0&times;10<sup>&#8722;4</sup>|-|Q, 1.1&times;10<sup>&#8722;4</sup>|-|Q; notes identical for all rows; same type
- henry 8141;8142: species '1-methyl-4-(1-methylethyl)-benzene', reference 2530: values 5.4&times;10<sup>&#8722;4</sup>|-|Q, 5.5&times;10<sup>&#8722;4</sup>|-|Q; notes identical for all rows; same type
- henry 8850;8851: species 'naphthalene', reference 2375: values 2.5&times;10<sup>&#8722;2</sup>|5100|V, 2.3&times;10<sup>&#8722;2</sup>|5600|V; notes identical for all rows; same type
- henry 11219;11220: species '3-methyl-3-octanol', reference 3406: values 1.3&times;10<sup>&#8722;1</sup>|-|Q, 1.6&times;10<sup>&#8722;1</sup>|-|Q; notes identical for all rows; same type
- henry 11217;11218: species '3-methyl-3-octanol', reference yaws2003handbook: values 5.4&times;10<sup>&#8722;2</sup>|-|X, 4.8&times;10<sup>&#8722;2</sup>|-|X; notes identical for all rows; same type
- henry 11263;11264: species '3-ethyl-2-heptanol', reference 3406: values 7.1&times;10<sup>&#8722;2</sup>|-|Q, 5.8&times;10<sup>&#8722;2</sup>|-|Q; notes identical for all rows; same type
- henry 11476;11477: species '3-ethyl-2,4-dimethyl-3-pentanol', reference 3406: values 3.7&times;10<sup>&#8722;2</sup>|-|Q, 3.6&times;10<sup>&#8722;2</sup>|-|Q; notes identical for all rows; same type
- henry 11474;11475: species '3-ethyl-2,4-dimethyl-3-pentanol', reference yaws2003handbook: values 4.9&times;10<sup>&#8722;2</sup>|-|X, 4.8&times;10<sup>&#8722;2</sup>|-|X; notes identical for all rows; same type
- henry 11824;11825: species '2-methyl-3-(1-methylethyl)-3-hexanol', reference 1115: values 9.6&times;10<sup>&#8722;1</sup>|-|Q, 1.2|-|Q; notes identical for all rows; same type
- henry 11820;11821: species '2-methyl-3-(1-methylethyl)-3-hexanol', reference 3406: values 2.1&times;10<sup>&#8722;2</sup>|-|Q, 1.7&times;10<sup>&#8722;2</sup>|-|Q; notes identical for all rows; same type
- henry 11818;11819: species '2-methyl-3-(1-methylethyl)-3-hexanol', reference yaws2003handbook: values 4.3&times;10<sup>&#8722;2</sup>|-|X, 3.7&times;10<sup>&#8722;2</sup>|-|X; notes identical for all rows; same type
- henry 12795;12796: species 'methanediol', reference 3563: values 4.0&times;10<sup>3</sup>|-|T, 7.1&times;10<sup>2</sup>|-|T; notes identical for all rows; same type
- henry 12797;12798: species '1,1-ethanediol', reference 3563: values 4.0&times;10<sup>1</sup>|-|T, 1.4&times;10<sup>1</sup>|-|T; notes identical for all rows; same type
- henry 15697;15698: species 'propanone', reference 1492: values 2.5&times;10<sup>&#8722;1</sup>|-|M, 3.2&times;10<sup>&#8722;1</sup>|-|M; notes identical for all rows; same type
- henry 15893;15894: species '3-pentanone', reference 636: values 1.2&times;10<sup>&#8722;1</sup>|-|V, 8.4&times;10<sup>&#8722;2</sup>|-|V; notes identical for all rows; same type
- henry 19417;19418: species 'methanoic acid', reference 538: values 5.1&times;10<sup>1</sup>|-|C, 5.3&times;10<sup>1</sup>|-|C; notes identical for all rows; same type
- henry 19457;19458: species 'ethanoic acid', reference 538: values 5.2&times;10<sup>1</sup>|-|C, 8.5&times;10<sup>1</sup>|-|C; notes identical for all rows; same type
- henry 19920;19921: species '2-hydroxy-benzoic acid', reference 636: values 6.9&times;10<sup>2</sup>|-|V, 1.8|-|V; notes identical for all rows; same type
- henry 19930;19931: species 'benzeneethanoic acid', reference 636: values 1.8&times;10<sup>2</sup>|-|V, 1.4&times;10<sup>1</sup>|-|V; notes identical for all rows; same type
- henry 20023;20024: species 'propanedioic acid', reference 3022: values 3.8&times;10<sup>8</sup>|11000|V, 9.3&times;10<sup>7</sup>|14000|V; notes identical for all rows; same type
- henry 20035;20036: species 'butanedioic acid', reference 3022: values 4.1&times;10<sup>7</sup>|11000|V, 2.0&times;10<sup>7</sup>|12000|V; notes identical for all rows; same type
- henry 20048;20049: species 'pentanedioic acid', reference 3022: values 5.1&times;10<sup>7</sup>|12000|V, 2.4&times;10<sup>7</sup>|13000|V; notes identical for all rows; same type
- henry 22147;22148: species 'dipropyl phthalate', reference 2957: values 1.8&times;10<sup>1</sup>|-|V, 3.3|-|V; notes identical for all rows; same type
- henry 23346;23347: species '2-methoxy-2-methylbutane', reference yaws2003handbook: values 4.2&times;10<sup>&#8722;3</sup>|-|X, 3.9&times;10<sup>&#8722;3</sup>|-|X; notes identical for all rows; same type
- henry 25302;25303: species 'milbemectin', reference 3549: values 6.5&times;10<sup>2</sup>|-|?, 3.9&times;10<sup>2</sup>|-|?; notes identical for all rows; same type
- henry 25314;25315: species 'pyrethrum', reference 3549: values 1.4&times;10<sup>4</sup>|-|?, 1.3&times;10<sup>1</sup>|-|?; notes identical for all rows; same type
- henry 27706;27707: species 'spiroxamine', reference 3549: values 4.0&times;10<sup>2</sup>|-|?, 2.0&times;10<sup>2</sup>|-|?; notes identical for all rows; same type
- ... 35 more in `reports/inconsistencies.csv`

## 3. Negative temperature dependence (14 rows)

Not necessarily wrong (solubility rising with temperature is known for some gases), but listed for a second look:

- henry 645: d ln H/d(1/T) = -700 K (solubility increases with temperature); species 'helium', reference 3714, type M, notes 42
- henry 665: d ln H/d(1/T) = -990 K (solubility increases with temperature); species 'neon', reference 3714, type M, notes -
- henry 1426: d ln H/d(1/T) = -3600 K (solubility increases with temperature); species '2-methylhexane', reference 903, type M, notes 282;283
- henry 12390: d ln H/d(1/T) = -3200 K (solubility increases with temperature); species '1-hydroxy-2,4-dimethylbenzene', reference 1156, type M, notes 33;279
- henry 15775: d ln H/d(1/T) = -5100 K (solubility increases with temperature); species 'butanone', reference 1156, type M, notes 33;279
- henry 24858: d ln H/d(1/T) = -730 K (solubility increases with temperature); species '2-methoxyethanol', reference 1156, type M, notes 541;42;279
- henry 26501: d ln H/d(1/T) = -2300 K (solubility increases with temperature); species 'pyridine', reference 1107, type M, notes -
- henry 26862: d ln H/d(1/T) = -2500 K (solubility increases with temperature); species '3-methylindole', reference 3799, type M, notes -
- henry 32458: d ln H/d(1/T) = -840 K (solubility increases with temperature); species 'tetrafluoromethane', reference 2610, type Q, notes -
- henry 32994: d ln H/d(1/T) = -390 K (solubility increases with temperature); species 'di(2,2,2-trifluoroethyl) ether', reference 3693, type V, notes 33
- henry 33385: d ln H/d(1/T) = -630 K (solubility increases with temperature); species 'chloromethane', reference usepa82, type X, notes 299
- henry 36915: d ln H/d(1/T) = -6000 K (solubility increases with temperature); species "2,2',4,4'-tetrachlorobiphenyl", reference 2496, type M, notes -
- henry 41375: d ln H/d(1/T) = -210 K (solubility increases with temperature); species 'dichlorodifluoromethane', reference usepa82, type X, notes 299
- henry 42886: d ln H/d(1/T) = -6700 K (solubility increases with temperature); species "2,2',4,4',5-pentabromodiphenyl ether", reference 2496, type M, notes 42

## 4. References and DOIs

47 literature rows are cited by no henry row; 33 of them are cited in notes. The 14 below are cited nowhere in the tables (several look like background references from the text of the paper):

- literature 73: reference 2413 (Battino and Clever (1966)) is cited by no henry row and no note
- literature 96: reference 3802 (Bettin and Spieweck (1990)) is cited by no henry row and no note
- literature 124: reference 1064 (Brennan et al. (1998)) is cited by no henry row and no note
- literature 405: reference 3775 (Heller et al. (2015)) is cited by no henry row and no note
- literature 408: reference 2606 (Henry (1803)) is cited by no henry row and no note
- literature 537: reference 3099 (Kurtén et al. (2015)) is cited by no henry row and no note
- literature 636: reference 2607 (Markham and Kobe (1941)) is cited by no henry row and no note
- literature 825: reference 958 (Sander (1999)) is cited by no henry row and no note
- literature 826: reference 2000 (Sander (2015)) is cited by no henry row and no note
- literature 828: reference 3509 (Sander et al. (2022)) is cited by no henry row and no note
- literature 863: reference 3767 (Schumpe (1993)) is cited by no henry row and no note
- literature 880: reference 3102 (Setschenow (1889)) is cited by no henry row and no note
- literature 908: reference 2104 (Smith and Harvey (2007)) is cited by no henry row and no note
- literature 1003: reference 3746 (Weisenberger and Schumpe (1996)) is cited by no henry row and no note

DOIs shared by more than one reference (chapters of one book may be intended):

- literature 671;864: DOI 10.1007/978-3-642-61445-3_6 used by references 671 (Mirabel et al. (1996)), 672 (Schurath et al. (1996))
- literature 625;626;627;628: DOI 10.1201/9781420044393 used by references 2611 (Mackay et al. (2006a)), 2612 (Mackay et al. (2006b)), 2613 (Mackay et al. (2006c)), 2614 (Mackay et al. (2006d))

The doi column of the literature table is never filled; 942 of 1076 bibliographies contain a doi.org link.

## 5. Values far from the other values for the same species

1273 rows differ by more than a factor of 1000 from the median of the values for the same species (species with at least three plain values; limits and type W excluded). Many will be genuine (e.g. effective constants, QSPR outliers); they are listed only in the CSV (category value_far_from_species_median).

## 6. Other observations

- 968 rows give a temperature dependence but no Hscp value.
- 233 rows give neither an Hscp value nor a temperature dependence; each of them has at least one note.
- 12 rows carry the infinity sign (&#8734;) as the value (type E).
- 72 rows have type W; none carries a value in the dump.
- 3199 species have no CAS RN and 13 no InChIKey; all given CAS RNs pass the check-digit test and all InChIKeys are well formed; no CAS RN or InChIKey is shared by two species.

## 7. Live site and the 2023 zip

The live site differs from henry_5.0.0_sql.zip in places that the errata page does not mention. Comparing the live notes and references pages with the dump gives 215 differences (the data rows themselves were compared only on the 4 species pages read for the errata):

- notes / digits only (e.g. refitted coefficients): 200
- literature / text: 10
- literature / letter case only: 3
- notes / letter case only: 1
- literature / digits only (e.g. refitted coefficients): 1

Most are three-parameter fits whose coefficients changed in the fourth or fifth digit, for example:

- note 534: `sup>= exp( &#8722;157.10556 +10203.60762/T +20.42555&nbsp;ln(T))&nbsp;mol&nbsp;m<sup>&#8722;3</sup>&nbsp;Pa<sup>&#8722;1</sup>, with T in K.` -> `sup>= exp( &#8722;157.10519 +10203.59116/T +20.42550&nbsp;ln(T))&nbsp;mol&nbsp;m<sup>&#8722;3</sup>&nbsp;Pa<sup>&#8722;1</sup>, with T in K.`
- note 4: `/sup>= exp( &#8722;130.91491 +6700.12242/T +17.04684&nbsp;ln(T))&nbsp;mol&nbsp;m<sup>&#8722;3</sup>&nbsp;Pa<sup>&#8722;1</sup>, with T in K.` -> `/sup>= exp( &#8722;130.91527 +6700.13828/T +17.04690&nbsp;ln(T))&nbsp;mol&nbsp;m<sup>&#8722;3</sup>&nbsp;Pa<sup>&#8722;1</sup>, with T in K.`
- note 8: `/sup>= exp( &#8722;179.13831 +8707.17767/T +24.33473&nbsp;ln(T))&nbsp;mol&nbsp;m<sup>&#8722;3</sup>&nbsp;Pa<sup>&#8722;1</sup>, with T in K.` -> `/sup>= exp( &#8722;179.13838 +8707.18054/T +24.33474&nbsp;ln(T))&nbsp;mol&nbsp;m<sup>&#8722;3</sup>&nbsp;Pa<sup>&#8722;1</sup>, with T in K.`

An updated SQL dump (or a changelog) would let users pick up such changes without reading every page.
