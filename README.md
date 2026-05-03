# md-img-localizer

扫描 Markdown 文件中的图片链接, 下载远程图片到 .asset/ 目录, 替换 Markdown 中的图片链接为本地路径

### ✅ 能力清单

* 精确匹配 `![](...)`（支持 title）
* 并发下载（线程池）
* 去重（URL hash + 本地缓存 index.json）
* 失败重试（指数退避）
* 增量执行（不会重复下载）
* 批量处理目录
* 可扩展 CLI 参数

---

# 📦 使用方式

```bash
pip install requests

# 单文件
python md_img_localizer.py README.md

# 目录（递归处理）
python md_img_localizer.py ./docs

# 控制并发
python md_img_localizer.py ./docs -w 16
```

---

# 📁 输出结构

```text
docs/
 ├── a.md
 ├── b.md
 └── .asset/
      ├── index.json
      ├── a1b2c3.png
      └── xxx.jpg
```
