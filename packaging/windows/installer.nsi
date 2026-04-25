; DownloadThis NSIS Installer
; Requires NSIS 3.x + nsProcess plugin

Unicode True

!define APP_NAME        "DownloadThis"
!define APP_ID          "dev.d4vram.downloadthis"
!define APP_VERSION     "2.0.0"
!define APP_PUBLISHER   "D4vRAM"
!define APP_URL         "https://github.com/D4vRAM369/downloadthis"
!define APP_EXE         "downloadthis.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\${APP_NAME}"
!define UNINSTALLER     "Uninstall.exe"
!define REG_UNINST      "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"

Name          "${APP_NAME} ${APP_VERSION}"
OutFile       "..\..\dist\downloadthis-${APP_VERSION}-setup.exe"
InstallDir    "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REG_UNINST}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; Modern UI
!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON      "..\icon.ico"
!define MUI_UNICON    "..\icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "English"

; ── Install ──────────────────────────────────────────────────
Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  File /r "..\..\dist\downloadthis\*.*"

  ; Shortcuts
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                  "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut  "$DESKTOP\${APP_NAME}.lnk" \
                  "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  ; Registry — uninstaller info
  WriteRegStr   HKLM "${REG_UNINST}" "DisplayName"      "${APP_NAME}"
  WriteRegStr   HKLM "${REG_UNINST}" "DisplayVersion"   "${APP_VERSION}"
  WriteRegStr   HKLM "${REG_UNINST}" "Publisher"        "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${REG_UNINST}" "URLInfoAbout"     "${APP_URL}"
  WriteRegStr   HKLM "${REG_UNINST}" "InstallLocation"  "$INSTDIR"
  WriteRegStr   HKLM "${REG_UNINST}" "UninstallString"  '"$INSTDIR\${UNINSTALLER}"'
  WriteRegDWORD HKLM "${REG_UNINST}" "NoModify"         1
  WriteRegDWORD HKLM "${REG_UNINST}" "NoRepair"         1

  WriteUninstaller "$INSTDIR\${UNINSTALLER}"
SectionEnd

; ── Uninstall ────────────────────────────────────────────────
Section "Uninstall"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"
  DeleteRegKey HKLM "${REG_UNINST}"
SectionEnd
