# Synthetic XLS fixture

`synthetic_credit.xls` contains four entirely fabricated test rows, never copied from the UCI customer data. It uses the official two-row header layout and `Data` worksheet so the real xlrd reader is exercised offline.

For row index `i` from 1 through 4: ID = i, LIMIT_BAL = 10000 × i, SEX = 1, EDUCATION = 2, MARRIAGE = 1, AGE = 20 + i, target = 1 only for i = 4. Every remaining cell is 0. Undocumented repayment zeros are intentional; Phase 2 reports rather than recodes them.

The fixture was generated with xlwt 1.3.0 installed only under ignored `artifacts/fixture_tools`; xlwt is not an application or test-runtime dependency. Tests need only the checked-in synthetic workbook and declared dependencies. To regenerate after an intentional schema change, the optional writer can be installed with:

```powershell
.venv\Scripts\python.exe -m pip install --target artifacts/fixture_tools xlwt==1.3.0
```

Create an xlwt workbook named `Data`, write the first row as blank, X1–X23, Y, the second row from `column_mapping()` source names in order, and the four synthetic rows defined above. This fixture does not establish real-world financial semantics; real-source verification uses the separate download/profile commands.
