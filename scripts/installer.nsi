;═══════════════════════════════════════════════════════════════════════════
;  CenSoloLTR-Search — Windows Installer (Bilingual: EN + ZH)
;  Built with NSIS 3.x   |   Build: makensis installer.nsi
;═══════════════════════════════════════════════════════════════════════════

Unicode true
ManifestDPIAware true

;─── Product ──────────────────────────────────────────────────────────────
!define PRODUCT_NAME        "CenSoloLTR-Search"
!ifndef PRODUCT_VERSION
  !define PRODUCT_VERSION   "1.0.0"
!endif
!define PRODUCT_PUBLISHER   "CenSoloLTR Lab"
!define PRODUCT_WEB_SITE    "https://github.com/xxx/CenSoloLTR-Search"
!define PRODUCT_REGKEY      "Software\${PRODUCT_NAME}"

;─── Compression ──────────────────────────────────────────────────────────
; NOTE: /SOLID causes integrity-check failures on Linux-built NSIS with
; large (2+ GB) payloads. Non-solid lzma is larger but stable.
SetCompressor lzma
CRCCheck on

;─── Modern UI 2 ──────────────────────────────────────────────────────────
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"

;─── Installer ────────────────────────────────────────────────────────────
Name              "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile           "${OUTPUT_DIR}\${PRODUCT_NAME}-Setup-${PRODUCT_VERSION}.exe"
InstallDir        "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey  HKLM "${PRODUCT_REGKEY}" "InstallDir"
RequestExecutionLevel admin
ShowInstDetails   show

;─── Branding ─────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON       "${RESOURCES_DIR}\icon.ico"
!define MUI_UNICON     "${RESOURCES_DIR}\icon.ico"

;═══════════════════════════════════════════════════════════════════════════
;  Pages
;═══════════════════════════════════════════════════════════════════════════

; --- Welcome ---
!define MUI_WELCOMEPAGE_TITLE        "$(WELCOME_TITLE)"
!define MUI_WELCOMEPAGE_TEXT         "$(WELCOME_TEXT)"

; --- License ---
!define MUI_LICENSEPAGE_TEXT_TOP     "$(LICENSE_TOP)"
!define MUI_LICENSEPAGE_TEXT_BOTTOM  "$(LICENSE_BOTTOM)"
!define MUI_LICENSEPAGE_BUTTON       "$(LICENSE_BUTTON)"

; --- Directory ---
!define MUI_DIRECTORYPAGE_TEXT_TOP       "$(DIR_TOP)"
!define MUI_DIRECTORYPAGE_TEXT_DESTINATION "$(DIR_DEST)"

; --- Components ---
!define MUI_COMPONENTSPAGE_TEXT_TOP       "$(COMP_TOP)"
!define MUI_COMPONENTSPAGE_TEXT_COMPLIST  "$(COMP_LIST)"
!define MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_TITLE "$(COMP_DESC_TITLE)"
!define MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_INFO  "$(COMP_DESC_INFO)"

; --- Finish ---
!define MUI_FINISHPAGE_TITLE          "$(FINISH_TITLE)"
!define MUI_FINISHPAGE_TEXT            "$(FINISH_TEXT)"
!define MUI_FINISHPAGE_RUN             "$INSTDIR\${PRODUCT_NAME}.exe"
!define MUI_FINISHPAGE_RUN_TEXT        "$(FINISH_RUN)"
!define MUI_FINISHPAGE_SHOWREADME      "$INSTDIR\docs"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "$(FINISH_DOC)"

;─── Insert pages ─────────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${RESOURCES_DIR}\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

;─── Uninstall ────────────────────────────────────────────────────────────
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;─── Languages ────────────────────────────────────────────────────────────
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

;═══════════════════════════════════════════════════════════════════════════
;  Language Strings (must be defined AFTER MUI_LANGUAGE)
;═══════════════════════════════════════════════════════════════════════════

;─── Welcome page ─────────────────────────────────────────────────────────
LangString WELCOME_TITLE   ${LANG_ENGLISH} "Welcome to ${PRODUCT_NAME} Setup"
LangString WELCOME_TITLE   ${LANG_SIMPCHINESE} "欢迎使用 ${PRODUCT_NAME} 安装向导"

LangString WELCOME_TEXT    ${LANG_ENGLISH} \
    "${PRODUCT_NAME} is a cross-species SoloLTR transposable element database $\r$\n\
    integrating annotation data from 18 legume species into a unified, $\r$\n\
    interactive desktop application.$\r$\n$\r$\n\
    Features:$\r$\n\
      - Interactive genome browser with centromere region highlighting$\r$\n\
      - BLAST sequence search with SoloLTR / Complete_LTR classification$\r$\n\
      - Statistical charts and superfamily distribution analysis$\r$\n\
      - Sequence download and export functions$\r$\n$\r$\n\
    This wizard will guide you through the installation.$\r$\n$\r$\n\
    Click Next to continue."

LangString WELCOME_TEXT    ${LANG_SIMPCHINESE} \
    "${PRODUCT_NAME} 是一个跨物种的 SoloLTR 转座元件数据库桌面软件，$\r$\n\
    收录了 18 种豆科植物的 SoloLTR 注释数据，整合到一个统一的、$\r$\n\
    可交互的桌面应用中。$\r$\n$\r$\n\
    主要功能:$\r$\n\
      - 交互式基因组浏览器，支持着丝粒区域高亮显示$\r$\n\
      - BLAST 序列搜索，自动区分 SoloLTR / Complete_LTR 类型$\r$\n\
      - 统计图表与超家族分布分析$\r$\n\
      - 序列下载与导出功能$\r$\n$\r$\n\
    本向导将引导您完成安装过程。$\r$\n$\r$\n\
    单击「下一步」继续。"

;─── License page ─────────────────────────────────────────────────────────
LangString LICENSE_TOP     ${LANG_ENGLISH}      "Please review the license agreement."
LangString LICENSE_TOP     ${LANG_SIMPCHINESE}  "请阅读以下许可协议。"
LangString LICENSE_BOTTOM  ${LANG_ENGLISH}      "If you accept the terms, click I Agree to continue."
LangString LICENSE_BOTTOM  ${LANG_SIMPCHINESE}  "如果您接受协议条款，请单击「我同意」继续安装。"
LangString LICENSE_BUTTON  ${LANG_ENGLISH}      "I &Agree"
LangString LICENSE_BUTTON  ${LANG_SIMPCHINESE}  "我同意(&A)"

;─── Directory page ───────────────────────────────────────────────────────
LangString DIR_TOP         ${LANG_ENGLISH}      "Select the installation folder."
LangString DIR_TOP         ${LANG_SIMPCHINESE}  "选择安装目录。"
LangString DIR_DEST        ${LANG_ENGLISH}      "Destination Folder"
LangString DIR_DEST        ${LANG_SIMPCHINESE}  "目标文件夹"

;─── Components page ──────────────────────────────────────────────────────
LangString COMP_TOP        ${LANG_ENGLISH}      "Choose which components to install."
LangString COMP_TOP        ${LANG_SIMPCHINESE}  "选择要安装的组件。"
LangString COMP_LIST       ${LANG_ENGLISH}      "Select or deselect components.$\r$\n$\r$\nRequired items cannot be unchecked."
LangString COMP_LIST       ${LANG_SIMPCHINESE}  "勾选或取消勾选组件。$\r$\n$\r$\n必选组件无法取消。"
LangString COMP_DESC_TITLE ${LANG_ENGLISH}      "Component Description"
LangString COMP_DESC_TITLE ${LANG_SIMPCHINESE}  "组件说明"
LangString COMP_DESC_INFO  ${LANG_ENGLISH}      "Hover over a component to see its description."
LangString COMP_DESC_INFO  ${LANG_SIMPCHINESE}  "将鼠标悬停在组件上可查看详细说明。"

;─── Finish page ──────────────────────────────────────────────────────────
LangString FINISH_TITLE    ${LANG_ENGLISH}      "Setup Complete"
LangString FINISH_TITLE    ${LANG_SIMPCHINESE}  "安装完成"
LangString FINISH_TEXT     ${LANG_ENGLISH}      "${PRODUCT_NAME} ${PRODUCT_VERSION} is ready to use."
LangString FINISH_TEXT     ${LANG_SIMPCHINESE}  "${PRODUCT_NAME} ${PRODUCT_VERSION} 已准备就绪。"
LangString FINISH_RUN      ${LANG_ENGLISH}      "Launch ${PRODUCT_NAME}"
LangString FINISH_RUN      ${LANG_SIMPCHINESE}  "启动 ${PRODUCT_NAME}"
LangString FINISH_DOC      ${LANG_ENGLISH}      "View Documentation"
LangString FINISH_DOC      ${LANG_SIMPCHINESE}  "查看文档"

;─── Start Menu ───────────────────────────────────────────────────────────
LangString SM_FOLDER       ${LANG_ENGLISH}      "${PRODUCT_NAME}"
LangString SM_FOLDER       ${LANG_SIMPCHINESE}  "${PRODUCT_NAME}"
LangString SM_APP          ${LANG_ENGLISH}      "${PRODUCT_NAME}"
LangString SM_APP          ${LANG_SIMPCHINESE}  "${PRODUCT_NAME}"
LangString SM_UNINST       ${LANG_ENGLISH}      "Uninstall ${PRODUCT_NAME}"
LangString SM_UNINST       ${LANG_SIMPCHINESE}  "卸载 ${PRODUCT_NAME}"
LangString SM_DOC          ${LANG_ENGLISH}      "Documentation"
LangString SM_DOC          ${LANG_SIMPCHINESE}  "文档"

;─── Misc ─────────────────────────────────────────────────────────────────
LangString ALREADY_INSTALLED ${LANG_ENGLISH} \
    "${PRODUCT_NAME} is already installed.$\r$\n$\r$\nContinue with installation?"
LangString ALREADY_INSTALLED ${LANG_SIMPCHINESE} \
    "${PRODUCT_NAME} 已经安装。$\r$\n$\r$\n是否继续安装？"
LangString WIN10_REQUIRED   ${LANG_ENGLISH} \
    "${PRODUCT_NAME} requires Windows 10 or later."
LangString WIN10_REQUIRED   ${LANG_SIMPCHINESE} \
    "${PRODUCT_NAME} 需要 Windows 10 或更高版本。"

;─── Component names ──────────────────────────────────────────────────────
LangString SEC_APP_NAME    ${LANG_ENGLISH}      "Application"
LangString SEC_APP_NAME    ${LANG_SIMPCHINESE}  "主程序"
LangString SEC_BLAST_NAME  ${LANG_ENGLISH}      "BLAST+ Tools"
LangString SEC_BLAST_NAME  ${LANG_SIMPCHINESE}  "BLAST+ 工具"
LangString SEC_DB_NAME     ${LANG_ENGLISH}      "Database"
LangString SEC_DB_NAME     ${LANG_SIMPCHINESE}  "数据库文件"
LangString SEC_DATA_NAME   ${LANG_ENGLISH}      "Annotation Data"
LangString SEC_DATA_NAME   ${LANG_SIMPCHINESE}  "注释数据"
LangString SEC_FASTA_NAME  ${LANG_ENGLISH}      "SoloLTR FASTA Sequences"
LangString SEC_FASTA_NAME  ${LANG_SIMPCHINESE}  "SoloLTR FASTA 序列"
LangString SEC_DOCS_NAME   ${LANG_ENGLISH}      "Documentation"
LangString SEC_DOCS_NAME   ${LANG_SIMPCHINESE}  "文档"
LangString SEC_SHORTCUT_NAME ${LANG_ENGLISH}    "Shortcuts"
LangString SEC_SHORTCUT_NAME ${LANG_SIMPCHINESE} "快捷方式"

;─── Component descriptions ───────────────────────────────────────────────
LangString DESC_APP        ${LANG_ENGLISH} \
    "Core GUI application with embedded Python runtime.$\r$\n$\r$\nRequired. (~180 MB)"
LangString DESC_APP        ${LANG_SIMPCHINESE} \
    "核心图形界面程序及嵌入式 Python 运行环境。$\r$\n$\r$\n必选组件。(~180 MB)"

LangString DESC_BLAST      ${LANG_ENGLISH} \
    "NCBI BLAST+ command-line tools (makeblastdb, blastn) for local sequence similarity search.$\r$\n$\r$\nRequired for BLAST Search functionality. (~30 MB)"
LangString DESC_BLAST      ${LANG_SIMPCHINESE} \
    "NCBI BLAST+ 命令行工具 (makeblastdb, blastn)，用于本地序列相似性搜索。$\r$\n$\r$\nBLAST 搜索功能依赖此组件。(~30 MB)"

LangString DESC_DB         ${LANG_ENGLISH} \
    "SQLite databases with 486,362 SoloLTR annotations across 18 legume species.$\r$\n$\r$\nRequired. (~290 MB)"
LangString DESC_DB         ${LANG_SIMPCHINESE} \
    "SQLite 数据库，包含 18 个物种共 486,362 条 SoloLTR 注释记录。$\r$\n$\r$\n必选组件。(~290 MB)"

LangString DESC_DATA       ${LANG_ENGLISH} \
    "Genome annotations: CEN BED regions, final annotation tables (CEN + Arm), genome information, NR LTR libraries, and genome data index. (~430 MB)"
LangString DESC_DATA       ${LANG_SIMPCHINESE} \
    "基因组注释数据：着丝粒 BED 区域、最终注释表格（着丝粒 + 染色体臂区间）、基因组信息、非冗余 LTR 文库与基因组数据索引。(~430 MB)"

LangString DESC_FASTA      ${LANG_ENGLISH} \
    "SoloLTR nucleotide FASTA sequences for CEN and Arm regions across 18 legume species.$\r$\n$\r$\nRequired for sequence export and some genome browser features. (~1.1 GB)"
LangString DESC_FASTA      ${LANG_SIMPCHINESE} \
    "18 个豆科物种着丝粒和染色体臂区间的 SoloLTR 核酸 FASTA 序列文件。$\r$\n$\r$\n序列导出和部分基因组浏览器功能依赖此组件。(~1.1 GB)"

LangString DESC_DOCS       ${LANG_ENGLISH} \
    "Technical architecture documentation and packaging guide. (~5 MB)"
LangString DESC_DOCS       ${LANG_SIMPCHINESE} \
    "技术架构文档与打包指南。(~5 MB)"

LangString DESC_SHORTCUT   ${LANG_ENGLISH} \
    "Start Menu and Desktop shortcuts for quick access."
LangString DESC_SHORTCUT   ${LANG_SIMPCHINESE} \
    "在开始菜单和桌面创建快捷方式，方便快速启动。"

;═══════════════════════════════════════════════════════════════════════════
;  Sections
;═══════════════════════════════════════════════════════════════════════════

Function .onInit
    ${IfNot} ${AtLeastWin10}
        MessageBox MB_OK|MB_ICONSTOP "$(WIN10_REQUIRED)"
        Abort
    ${EndIf}

    ReadRegStr $0 HKLM "${PRODUCT_REGKEY}" "InstallDir"
    ${If} $0 != ""
        MessageBox MB_YESNO|MB_ICONQUESTION "$(ALREADY_INSTALLED)" IDYES +2
        Abort
    ${EndIf}
FunctionEnd

;─── Application (Required) ──────────────────────────────────────────────
Section "!$(SEC_APP_NAME)" SecApp
    SectionIn RO
    SetOutPath "$INSTDIR"

    File "${STAGE_DIR}\${PRODUCT_NAME}.exe"
    WriteUninstaller "$INSTDIR\uninst.exe"

    WriteRegStr HKLM "${PRODUCT_REGKEY}" "InstallDir"     "$INSTDIR"
    WriteRegStr HKLM "${PRODUCT_REGKEY}" "Version"        "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_REGKEY}" "DisplayName"    "${PRODUCT_NAME}"
    WriteRegStr HKLM "${PRODUCT_REGKEY}" "Publisher"      "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "${PRODUCT_REGKEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "${PRODUCT_REGKEY}" "DisplayIcon"     "$INSTDIR\${PRODUCT_NAME}.exe"
    WriteRegDWORD HKLM "${PRODUCT_REGKEY}" "NoModify"     "1"
    WriteRegDWORD HKLM "${PRODUCT_REGKEY}" "NoRepair"     "1"

    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayName" "${PRODUCT_NAME} ${PRODUCT_VERSION}"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayIcon" "$INSTDIR\${PRODUCT_NAME}.exe"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayVersion" "${PRODUCT_VERSION}"
SectionEnd

;─── BLAST+ ───────────────────────────────────────────────────────────────
Section "$(SEC_BLAST_NAME)" SecBlast
    SetOutPath "$INSTDIR\blast"
    File /nonfatal /r "${STAGE_DIR}\blast\*"
SectionEnd

;─── Database (Required) ──────────────────────────────────────────────────
Section "!$(SEC_DB_NAME)" SecDB
    SectionIn RO
    SetOutPath "$INSTDIR\data"
    File /nonfatal "${STAGE_DIR}\data\ltr.sqlite"
    File /nonfatal "${STAGE_DIR}\data\annotation.sqlite"
SectionEnd

;─── Annotation Data ──────────────────────────────────────────────────────
Section "$(SEC_DATA_NAME)" SecData
    ; Genome information (genome_information.txt + Source PDFs)
    SetOutPath "$INSTDIR\data\0.1.genome_information"
    File /nonfatal /r "${STAGE_DIR}\data\0.1.genome_information\*"

    ; Genome data index
    SetOutPath "$INSTDIR\data\0.genome_data_index"
    File /nonfatal /r "${STAGE_DIR}\data\0.genome_data_index\*"

    ; NR LTR Libraries (for BLAST search)
    SetOutPath "$INSTDIR\data\0.NonRedundant_LTR_Libraries"
    File /nonfatal /r "${STAGE_DIR}\data\0.NonRedundant_LTR_Libraries\*"

    ; CEN BED regions (for genome browser)
    SetOutPath "$INSTDIR\data\2.CEN_region_Bed"
    File /nonfatal /r "${STAGE_DIR}\data\2.CEN_region_Bed\*.bed"

    ; CEN final annotations (TSV)
    SetOutPath "$INSTDIR\data\10.CEN_PeriCEN_Final_Annotations_1"
    File /nonfatal /r "${STAGE_DIR}\data\10.CEN_PeriCEN_Final_Annotations_1\*"

    ; Arm final annotations (TSV)
    SetOutPath "$INSTDIR\data\12.Arm_Final_Annotations_1"
    File /nonfatal /r "${STAGE_DIR}\data\12.Arm_Final_Annotations_1\*"
SectionEnd

;─── SoloLTR FASTA Sequences ──────────────────────────────────────────────
Section "$(SEC_FASTA_NAME)" SecFasta
    ; CEN SoloLTR FASTA
    SetOutPath "$INSTDIR\data\11.CEN_PeriCEN_SoloLTR_FASTA_1"
    File /nonfatal /r "${STAGE_DIR}\data\11.CEN_PeriCEN_SoloLTR_FASTA_1\*"

    ; Arm SoloLTR FASTA
    SetOutPath "$INSTDIR\data\13.Arm_SoloLTR_FASTA_1"
    File /nonfatal /r "${STAGE_DIR}\data\13.Arm_SoloLTR_FASTA_1\*"
SectionEnd

;─── Documentation ────────────────────────────────────────────────────────
Section "$(SEC_DOCS_NAME)" SecDocs
    SetOutPath "$INSTDIR\docs"
    File /nonfatal /r "${STAGE_DIR}\docs\*.md"
    File /nonfatal /r "${STAGE_DIR}\docs\*.pdf"
SectionEnd

;─── Shortcuts ────────────────────────────────────────────────────────────
Section "$(SEC_SHORTCUT_NAME)" SecShortcuts
    CreateDirectory "$SMPROGRAMS\$(SM_FOLDER)"
    CreateShortCut "$SMPROGRAMS\$(SM_FOLDER)\$(SM_APP).lnk" \
        "$INSTDIR\${PRODUCT_NAME}.exe" "" "$INSTDIR\${PRODUCT_NAME}.exe"
    CreateShortCut "$SMPROGRAMS\$(SM_FOLDER)\$(SM_DOC).lnk" \
        "$INSTDIR\docs"
    CreateShortCut "$SMPROGRAMS\$(SM_FOLDER)\$(SM_UNINST).lnk" \
        "$INSTDIR\uninst.exe"
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" \
        "$INSTDIR\${PRODUCT_NAME}.exe" "" "$INSTDIR\${PRODUCT_NAME}.exe"
SectionEnd

;─── Descriptions ────────────────────────────────────────────────────────
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecApp}       "$(DESC_APP)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecBlast}     "$(DESC_BLAST)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDB}        "$(DESC_DB)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecData}      "$(DESC_DATA)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecFasta}     "$(DESC_FASTA)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDocs}      "$(DESC_DOCS)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecShortcuts} "$(DESC_SHORTCUT)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;═══════════════════════════════════════════════════════════════════════════
;  Uninstall
;═══════════════════════════════════════════════════════════════════════════

Section "Uninstall"
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\$(SM_FOLDER)"

    RMDir /r "$INSTDIR\blast"
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\docs"
    Delete "$INSTDIR\${PRODUCT_NAME}.exe"
    Delete "$INSTDIR\uninst.exe"
    RMDir  "$INSTDIR"

    DeleteRegKey HKLM "${PRODUCT_REGKEY}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
SectionEnd
