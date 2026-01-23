# Class Scheduler

A **Python tool** to help students find all valid combinations of classes based on course ids from [iau.ir](https://stdn.iau.ir/Student/).  
Input your class IDs (e.g., `زبان تخصصی` → `7000002171`) and see possible schedules **without conflicts**.

---

## Features

- Parse classes from HTML files
- Filter by class IDs
- Handle class and exam schedules
- Generate valid combinations of classes
- Display results as a table
---

## Installation

```bash
pip install beautifulsoup4 rich
```

## Usage
1. Put your HTML course files in the files/ folder.

2. Set the desired class IDs in main.py:
   ```py
   filters = {[7000002171, 7000020525, 1803185334] :'كد درس'} 
   ```

3. Run the scheduler:

    ```bash
    python src/main.py
    ```

4. Output shows valid class combinations:

    ```
    Combination 1:
   • عطیه عسگری | 1404/11/09 از 11:00 تا 13:00 | دوشنبه 13:00 تا 14:50 | 21252 
   • سمیرا راستبد | 1404/11/12 از 11:00 تا 13:00 | چهارشنبه 13:00 تا 14:50 | 21254 
   • مهری دهبان | 1404/10/11 از 11:00 تا 13:00 | چهارشنبه 16:00 تا 19:30 | 21258 
    ```

# Testing
```
python -m unittest discover -s src
```
