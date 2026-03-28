FONTS DIRECTORY
===============

Required fonts:
  NotoSansDevanagari-Regular.ttf
  NotoSansDevanagari-Bold.ttf

Purpose: Unicode font enabling Hindi (Devanagari) text in PDF reports.

HOW TO DOWNLOAD:
1. Visit: https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari
2. Click "Download family"
3. Extract the zip → go into the static/ subfolder
4. Copy NotoSansDevanagari-Regular.ttf and NotoSansDevanagari-Bold.ttf into this /fonts/ directory

Do NOT use the variable font files from the zip root — use the static/ versions only.

The app will gracefully fall back to English-only PDF if these files are missing.
Hindi PDF section will be skipped with a note explaining how to enable it.
