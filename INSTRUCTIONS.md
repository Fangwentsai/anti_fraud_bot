# 改進 load_potato_game_questions 函數的說明

為了確保 `potato_game_questions.json` 題庫正確加載，我們需要手動更新 `app.py` 中的 `load_potato_game_questions` 函數。

## 需要修改的地方

1. 找到 `app.py` 中約在第1100行的 `load_potato_game_questions` 函數:
```python
def load_potato_game_questions():
    global potato_game_questions
    try:
        with open(POTATO_GAME_QUESTIONS_DB, 'r', encoding='utf-8') as f:
            data = json.load(f)
            potato_game_questions = data.get("questions", [])
        logger.info(f"成功從 {POTATO_GAME_QUESTIONS_DB} 加載詐騙題庫，共 {len(potato_game_questions)} 道題目")
    except FileNotFoundError:
        logger.warning(f"詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 未找到。")
        potato_game_questions = []
    except json.JSONDecodeError:
        logger.error(f"解析詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 失敗。")
        potato_game_questions = []
    except Exception as e:
        logger.error(f"加載詐騙題庫時發生未知錯誤: {e}")
        potato_game_questions = []
```

2. 替換為以下優化版本:
```python
def load_potato_game_questions():
    global potato_game_questions
    try:
        # 記錄載入前的路徑信息
        file_path = os.path.abspath(POTATO_GAME_QUESTIONS_DB)
        logger.info(f"嘗試從路徑讀取題庫文件: {file_path}")
        logger.info(f"當前工作目錄: {os.getcwd()}")
        
        # 檢查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            potato_game_questions = []
            return
            
        with open(POTATO_GAME_QUESTIONS_DB, 'r', encoding='utf-8') as f:
            data = json.load(f)
            potato_game_questions = data.get("questions", [])
            
        # 確認文件內容
        first_three_questions = []
        for i, q in enumerate(potato_game_questions[:3]):
            first_three_questions.append(f"題目ID: {q.get('id')}, 詐騙類型: {q.get('fraud_type')}")
            
        logger.info(f"成功從 {POTATO_GAME_QUESTIONS_DB} 加載詐騙題庫，共 {len(potato_game_questions)} 道題目")
        logger.info(f"前三個題目: {', '.join(first_three_questions)}")
        logger.info(f"題庫中選項信息: 有預設選項的題目數量: {sum(1 for q in potato_game_questions if 'options' in q and q['options'] and 'correct_option' in q)}")
    except FileNotFoundError:
        logger.warning(f"詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 未找到。")
        potato_game_questions = []
    except json.JSONDecodeError:
        logger.error(f"解析詐騙題庫文件 {POTATO_GAME_QUESTIONS_DB} 失敗。")
        potato_game_questions = []
    except Exception as e:
        logger.error(f"加載詐騙題庫時發生未知錯誤: {e}")
        potato_game_questions = []
```

## 改進說明

這個優化版本主要添加了以下功能：

1. **路徑診斷**：記錄題庫文件的絕對路徑和當前工作目錄，方便排查路徑問題
2. **文件存在性檢查**：在嘗試打開文件前先檢查文件是否存在
3. **更詳細的日誌**：
   - 顯示前三個題目的基本信息
   - 統計有預設選項的題目數量
   - 記錄更多加載過程的細節

## 測試方法

修改完成後，重啟服務器，然後在日誌中查找類似以下的輸出：
```
嘗試從路徑讀取題庫文件: /完整路徑/potato_game_questions.json
當前工作目錄: /當前目錄
成功從 potato_game_questions.json 加載詐騙題庫，共 XX 道題目
前三個題目: 題目ID: 1, 詐騙類型: 網路購物詐騙, 題目ID: 2, 詐騙類型: ...
題庫中選項信息: 有預設選項的題目數量: XX
```

如果看到這些日誌，說明題庫加載正確。 