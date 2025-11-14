# Prompt Notebook

這個小工具提供一個可分類、可註解、支援修改與一鍵複製的提示詞筆記簿。所有資料都儲存在 `prompts.json` 檔案中，透過命令列即可完成管理。

## 安裝與環境

本專案使用標準 Python 3。無需額外套件即可執行，但若系統已安裝 `pyperclip`、`pbcopy`、`xclip`、`wl-copy` 或 Windows 的 `clip` 指令，即可啟動真正的剪貼簿複製功能。

```bash
python -m prompt_book --help
```

## 快速開始

初始化一個新的提示詞筆記簿並預先建立常見分類：

```bash
python -m prompt_book init
```

新增一則提示詞（支援角色、圖像、系統等任何分類）：

```bash
python -m prompt_book add "星際探險家" 角色 "請以第一人稱描述一位探索未知星系的隊長。" --notes "強調勇敢與好奇心"
```

列出所有提示詞：

```bash
python -m prompt_book list
```

當筆記越來越龐大時，可使用搜尋與排序參數快速定位資料：

```bash
python -m prompt_book list --search 星際 --sort title --ascending
python -m prompt_book list --category 角色 --sort created
```

顯示詳細內容或進行修改：

```bash
python -m prompt_book show <prompt-id>
python -m prompt_book update <prompt-id> --notes "加入對話語氣"
```

將內容一鍵複製到剪貼簿：

```bash
python -m prompt_book copy <prompt-id>
python -m prompt_book copy <prompt-id> --only content  # 只複製主體
```

刪除或管理分類：

```bash
python -m prompt_book delete <prompt-id>
python -m prompt_book categories --add 腳本
```

所有指令都支援 `--file` 參數，可自訂儲存檔案位置，便於同步或備份。
