# ⚡ FitGirl Multi-Part Downloader & DataNodes Auto-Clicker

A high-speed, multi-part download manager designed specifically for downloading split game archives (`.part01.rar`, `.part02.rar`, etc.) from filehosters like **DataNodes**.

---

## 🌟 ප්‍රධාන විශේෂාංග (Key Features)

1. **Multi-Day Resume (දවස් ගානක් PC එක Off කර කර බාන්න):**
   - 50GB-100GB ලොකු games බාද්දි PC එක එක දිගට දාලා තියන්න ඕන නෑ. රෑට PC එක Shutdown කරලා පහුවදා ආයෙ On කරාම ඊයේ නැවතුන තැන ඉඳන්ම Resume වෙනවා (0% වෙන්නේ නෑ!).
2. **Auto-Clicker & Direct Bridge:**
   - DataNodes වල Step 1 Ads, Scan Verification, සහ Step 2 (5s Countdown) manual click කරන්න ඕන නෑ. Auto-Clicker script එකෙන් ඔක්කොම auto click වෙලා direct download link එක auto tool එකට එනවා!
3. **No Python Needed on Windows:**
   - Standalone `.exe` එකක් විදියට run වෙන නිසා Windows යාලුවන්ට කිසිම software එකක් හෝ Python install කරන්න අවශ්‍ය නෑ.
4. **"Refresh Expired Link" Feature:**
   - DataNodes direct links පැය 24කට පස්සේ expire උනත්, බාපු GB ගාන delete කරන්නේ නැතුව Right-click කරලා අලුත් link එක දුන්නම එතනින්ම ඉතුරු ටික බානවා!
5. **Smart URL Filter:**
   - FitGirl webpage links බොරුවට download queue එකට දාලා fail කරන්නේ නෑ — ඇත්ත direct download files විතරක් ලස්සනට queue එකට වැටෙනවා.

---

## 🚀 පාවිච්චි කරන්නේ මෙහෙමයි (How to Use)

### පියවර 1: Tool එක Run කරගන්න
* **Windows පරිශීලකයින්:**
  - `FitGirlDownloader.exe` එක Double-Click කරලා Open කරගන්න (Python ඕන නෑ).
* **Mac පරිශීලකයින්:**
  - Terminal එකේ run කරන්න:
    ```bash
    python3 downloader.py
    ```

### පියවර 2: Browser එකට Auto-Clicker එක දාගන්න (විනාඩියයි යන්නේ)
1. **Chrome / Brave / Edge** වලට [Tampermonkey](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo) install කරගන්න (නැත්නම් Safari නම් Mac App Store එකෙන් "Userscripts").
2. Tampermonkey එකේ "Create a new script" ගිහින්, මෙතන තියෙන [`datanodes_autoclicker.user.js`](datanodes_autoclicker.user.js) එකේ code එක Paste කරලා **Save (Ctrl + S / Cmd + S)** කරන්න.

### පියවර 3: Download කරන්න!
1. FitGirl එකෙන් DataNodes links ටික Tool එකේ උඩ box එකට paste කරන්න.
2. **"🌐 Auto-Open in Browser"** කියන Button එක ඔබන්න.
3. Browser එකේ Tabs open වෙයි -> Script එකෙන් auto click වෙයි -> Direct links ටික auto Tool එකේ queue එකට ඇවිත් Full Speed එකෙන් බාන්න පටන් ගනියි!

---

## 📦 Windows Standalone EXE එක හදාගන්නේ කොහොමද?
ඔයාට මේ repository එකෙන් direct `.exe` එක හදාගන්න ක්‍රම 2ක් තියෙනවා:
1. **Windows PC එකකදි:** `build_windows_exe.bat` එක double-click කරන්න. `dist\FitGirlDownloader.exe` හැදෙයි.
2. **GitHub Actions (Auto Cloud Build):** මේ Repo එකේ GitHub Actions workflow එකෙන් සෑම Push එකකටම Windows Latest server එකක් උඩ automatically `FitGirlDownloader.exe` එක build කරලා artifact එකක් විදියට download කරන්න දෙනවා!
