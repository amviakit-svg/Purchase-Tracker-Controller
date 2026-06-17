t = open('frontend/index.html', encoding='utf-8').read()
import re
for fn in ['loadMasterPreview', 'resetIfBuilder', 'addIfConditionRow', 'buildIfPayload', 'updateFormulaUI', 'previewFormula']:
    m = re.search('function ' + fn + r'\b', t)
    line_no = t[:m.start()].count('\n') + 1
    print(f"{fn}: line {line_no}")