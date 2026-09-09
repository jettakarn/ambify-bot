# twoshiftly (2shiftly)

把**掃描班表 PDF**轉成行事曆（`.ics`）——**本機網頁介面**，離線 OCR，不用 API key。

目前針對 **國賓影城** 每日掃描班表。

## 快速開始（Windows）

1. 安裝 [Python 3.11+](https://www.python.org/downloads/)
2. 雙擊專案裡的 `run.bat`
3. 瀏覽器會開啟 `http://127.0.0.1:8765/`
4. 搜尋暱稱或員工代號 → 預覽班表 → 下載 `.ics` 或複製文字

第一次執行會自動安裝套件，並下載約 10MB 的 OCR 模型。

## 功能

- **網頁操作** — 上傳、選人、下載，不必打指令
- **100% 本機** — 班表不上傳雲端
- **時數檢查** — 畫面上會顯示可疑 OCR 警告
- **跨日班** — 自動判斷過夜班次
- **休假推估** — 當日未排班則標為休假

## 開發安裝

```bash
pip install -e ".[dev]"
pytest
```

手動啟動：

```bash
py -m twoshiftly.web
```

## 架構

```
PDF → pypdfium2 → RapidOCR → Ambassador layout → validate → filter → .ics
```

暫存與快取寫在系統暫存目錄（每次上傳獨立工作區）。

## 隱私

請勿把真實班表 PDF 提交進 git。

## License

MIT
