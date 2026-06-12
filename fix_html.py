# -*- coding: utf-8 -*-
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement_html = '''        <!-- ==================== UPLOAD & FILE MANAGEMENT ==================== -->\n        <div id="page-upload" class="page-content hidden">\n            <!-- Header + Upload Section Combined -->\n            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">\n                <!-- Compact Inline Header -->\n                <div class="flex items-center gap-3 mb-4 pb-3 border-b border-gray-100">\n                    <div class="flex items-center justify-center w-9 h-9 bg-blue-50 rounded-lg">\n                        <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">\n                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>\n                        </svg>\n                    </div>\n                    <h2 class="text-lg font-semibold text-gray-800">Upload Files</h2>\n                </div>\n                \n                <div class="mb-4">\n                    <label class="block text-sm font-medium text-gray-700 mb-2">Column Names <span class="text-red-500">*</span></label>\n                    <input type="text" id="master-column-names" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500" placeholder="e.g., Order ID, Amount, Tax - or type ALL to auto-pick every column">\n                    <p class="text-xs text-gray-500 mt-1">Enter column names separated by commas, or type <code class="bg-gray-100 px-1 rounded">ALL</code> to use every column from the first file. Column names must match exactly.</p>\n                </div>\n\n                <!-- Upload Controls - Full Width -->\n                <div class="flex flex-col lg:flex-row lg:items-end gap-3">\n                    <div class="flex-1">\n                        <div id="drop-zone" class="drop-zone rounded-lg p-3 text-center cursor-pointer border border-dashed border-gray-300 hover:border-blue-400 transition-colors">\n'''

assert '</div>' in lines[556], f'Expected </div> but got {lines[556]}'
assert 'file-input' in lines[557], f'Expected file-input but got {lines[557]}'

new_lines = lines[:341] + [replacement_html] + lines[557:]

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Fixed successfully! Total lines:', len(new_lines))
