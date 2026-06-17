"""Count duplicate function declarations to find issues."""
import re
import sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()
names = ['updateFormulaUI', 'previewFormula', 'applyFormula', 'loadFormulaColumns',
         'populateFormulaPrimaryColumns', 'populateFormulaSecondaryFiles',
         'loadFormulaSecondarySheets', 'loadFormulaSecondaryColumns',
         'updateFormulaHints', 'selectFormulaHint', 'validateFormulaColumns',
         'showFormulaProgress', 'hideFormulaProgress', 'openFormulaModal',
         'closeFormulaModal', 'resetFormulaForm',
         'addIfConditionRow', 'removeIfConditionRow', 'onIfCondChange',
         'updateIfBranchInputs', 'buildIfPayload', 'resetIfBuilder']
for name in names:
    matches = list(re.finditer(r'function\s+' + re.escape(name) + r'\b', text))
    print(f'{name}: {len(matches)}')