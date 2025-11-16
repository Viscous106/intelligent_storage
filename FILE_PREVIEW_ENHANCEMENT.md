# File Preview Enhancement - Complete Guide

## Overview

Enhanced file preview functionality that displays file content directly in the browser instead of forcing downloads. Now supports SQL, CSV, JSON, and many other file formats with rich preview capabilities.

## What Changed

### ✅ Before
- Clicking on files triggered immediate download
- No preview for text-based files
- Limited preview support

### ✨ After
- **SQL files**: Syntax-highlighted code preview
- **CSV files**: Interactive table preview with data type detection
- **JSON files**: Formatted and syntax-highlighted preview
- **Text/Code files**: Syntax-highlighted preview for 30+ languages
- **Images/Videos/Audio**: Inline media players
- **PDFs**: Inline PDF viewer
- Download still available as an option

---

## Supported File Formats

### 📄 Text & Code Files
- **.sql** - SQL with syntax highlighting
- **.py** - Python
- **.js, .ts, .jsx, .tsx** - JavaScript/TypeScript
- **.java, .cpp, .c, .h** - Java, C/C++
- **.php, .rb, .go, .rs** - PHP, Ruby, Go, Rust
- **.html, .css, .scss** - Web files
- **.xml, .yaml, .yml** - Config files
- **.sh, .bash** - Shell scripts
- **.txt, .md, .log** - Text files

### 📊 Data Files
- **.csv** - Table preview with:
  - Parsed headers and rows
  - Data type detection
  - Schema inference
  - Limited to first 100 rows for performance

- **.json** - Formatted preview with:
  - Syntax highlighting
  - Proper indentation
  - Structured data display

### 🎨 Media Files
- **Images**: .jpg, .png, .gif, .webp, .svg, .bmp
- **Videos**: .mp4, .webm, .mov, .avi, .mkv
- **Audio**: .mp3, .wav, .ogg, .m4a, .flac
- **PDFs**: Inline PDF viewer

### 📦 Other Files
- **Archives**: Contents listing for .zip, .tar, .gz
- **Documents**: .doc, .docx, .xls, .xlsx (download with suggestion)

---

## API Endpoints

### 1. Get Preview Data
```
GET /api/file_browser/api/preview/{file_id}/
```

Returns JSON with preview data including file content, metadata, and preview type.

**Response Structure:**
```json
{
  "success": true,
  "id": 123,
  "filename": "schema.sql",
  "extension": ".sql",
  "mime_type": "application/sql",
  "file_size": 2048,
  "file_size_human": "2.00 KB",
  "uploaded_at": "2025-11-16T10:30:00",
  "category": "code",
  "preview_type": "code",
  "can_preview": true,
  "content": "CREATE TABLE users...",
  "language": "sql",
  "lines": 25,
  "download_url": "/api/file_browser/api/download/123/"
}
```

### 2. Stream File Content
```
GET /api/file_browser/api/preview/content/{file_id}/
```

Streams file content with `Content-Disposition: inline` for direct browser display.

Used for images, videos, audio, and PDFs.

### 3. Download File
```
GET /api/file_browser/api/download/{file_id}/
```

Downloads the file with `Content-Disposition: attachment`.

---

## Usage Examples

### Example 1: Preview SQL File
```bash
curl http://localhost:8000/api/file_browser/api/preview/123/
```

**Response:**
```json
{
  "success": true,
  "filename": "user_schema.sql",
  "preview_type": "code",
  "language": "sql",
  "can_preview": true,
  "content": "-- SQL Schema\nCREATE TABLE users (\n  id SERIAL PRIMARY KEY,\n  ...\n)",
  "lines": 15
}
```

### Example 2: Preview CSV File
```bash
curl http://localhost:8000/api/file_browser/api/preview/456/
```

**Response:**
```json
{
  "success": true,
  "filename": "sales_data.csv",
  "preview_type": "csv",
  "can_preview": true,
  "csv_data": {
    "headers": ["id", "name", "amount", "date"],
    "rows": [
      ["1", "Product A", "100.50", "2025-01-15"],
      ["2", "Product B", "250.00", "2025-01-16"]
    ],
    "total_rows": 2,
    "total_columns": 4,
    "schema": {
      "id": {"type": "integer", "index": 0},
      "name": {"type": "string", "index": 1},
      "amount": {"type": "float", "index": 2},
      "date": {"type": "string", "index": 3}
    },
    "preview": false
  }
}
```

### Example 3: Preview JSON File
```bash
curl http://localhost:8000/api/file_browser/api/preview/789/
```

**Response:**
```json
{
  "success": true,
  "filename": "config.json",
  "preview_type": "json",
  "can_preview": true,
  "language": "json",
  "json_data": {
    "app": "intelligent_storage",
    "version": "1.0.0"
  },
  "content": "{\n  \"app\": \"intelligent_storage\",\n  \"version\": \"1.0.0\"\n}"
}
```

### Example 4: View Image
```bash
# Get preview metadata
curl http://localhost:8000/api/file_browser/api/preview/101/

# View image directly
curl http://localhost:8000/api/file_browser/api/preview/content/101/
```

---

## Frontend Integration

### JavaScript Example
```javascript
// Fetch preview data
async function previewFile(fileId) {
  const response = await fetch(`/api/file_browser/api/preview/${fileId}/`);
  const preview = await response.json();

  if (!preview.success) {
    console.error('Preview failed:', preview.error);
    return;
  }

  // Handle different preview types
  switch (preview.preview_type) {
    case 'code':
    case 'text':
      // Display syntax-highlighted code
      displayCode(preview.content, preview.language);
      break;

    case 'csv':
      // Display as table
      displayTable(preview.csv_data);
      break;

    case 'json':
      // Display formatted JSON
      displayJSON(preview.json_data);
      break;

    case 'image':
      // Display image
      displayImage(preview.preview_url);
      break;

    case 'video':
      // Show video player
      displayVideo(preview.stream_url);
      break;

    default:
      // Show download button
      showDownload(preview.download_url);
  }
}

// Display code with syntax highlighting
function displayCode(content, language) {
  const codeElement = document.getElementById('code-preview');
  codeElement.innerHTML = `<pre><code class="language-${language}">${escapeHtml(content)}</code></pre>`;
  // Use highlight.js or similar for syntax highlighting
  hljs.highlightElement(codeElement.querySelector('code'));
}

// Display CSV as table
function displayTable(csvData) {
  let html = '<table class="preview-table">';

  // Headers
  html += '<thead><tr>';
  csvData.headers.forEach(header => {
    const type = csvData.schema[header]?.type || 'string';
    html += `<th>${header} <span class="type">${type}</span></th>`;
  });
  html += '</tr></thead>';

  // Rows
  html += '<tbody>';
  csvData.rows.forEach(row => {
    html += '<tr>';
    row.forEach(cell => {
      html += `<td>${escapeHtml(cell)}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';

  if (csvData.preview) {
    html += `<p class="info">Showing first ${csvData.rows.length} of ${csvData.total_rows} rows</p>`;
  }

  document.getElementById('table-preview').innerHTML = html;
}

// Display formatted JSON
function displayJSON(jsonData) {
  const formatted = JSON.stringify(jsonData, null, 2);
  displayCode(formatted, 'json');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
```

### React Example
```jsx
import React, { useState, useEffect } from 'react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';

function FilePreview({ fileId }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`/api/file_browser/api/preview/${fileId}/`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setPreview(data);
        } else {
          setError(data.error);
        }
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [fileId]);

  if (loading) return <div>Loading preview...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!preview.can_preview) {
    return (
      <div>
        <p>{preview.message}</p>
        <a href={preview.download_url} download>Download File</a>
      </div>
    );
  }

  // Render based on preview type
  if (preview.preview_type === 'code' || preview.preview_type === 'text') {
    return (
      <div>
        <h3>{preview.filename}</h3>
        <p>{preview.lines} lines • {preview.file_size_human}</p>
        <SyntaxHighlighter language={preview.language} style={docco}>
          {preview.content}
        </SyntaxHighlighter>
      </div>
    );
  }

  if (preview.preview_type === 'csv') {
    return (
      <div>
        <h3>{preview.filename}</h3>
        <CSVTable data={preview.csv_data} />
      </div>
    );
  }

  if (preview.preview_type === 'json') {
    return (
      <div>
        <h3>{preview.filename}</h3>
        <SyntaxHighlighter language="json" style={docco}>
          {preview.content}
        </SyntaxHighlighter>
      </div>
    );
  }

  if (preview.preview_type === 'image') {
    return (
      <div>
        <h3>{preview.filename}</h3>
        <img src={preview.preview_url} alt={preview.filename} />
      </div>
    );
  }

  if (preview.preview_type === 'video') {
    return (
      <div>
        <h3>{preview.filename}</h3>
        <video controls src={preview.stream_url} />
      </div>
    );
  }

  return <div>Preview not available</div>;
}

function CSVTable({ data }) {
  return (
    <>
      <table className="csv-preview">
        <thead>
          <tr>
            {data.headers.map((header, i) => (
              <th key={i}>
                {header}
                <span className="type">{data.schema[header]?.type}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.preview && (
        <p>Showing {data.rows.length} of {data.total_rows} rows</p>
      )}
    </>
  );
}

export default FilePreview;
```

---

## Preview Types

| Preview Type | Description | Features |
|--------------|-------------|----------|
| `code` | Source code files | Syntax highlighting, line numbers, language detection |
| `text` | Plain text files | Simple text display |
| `csv` | CSV data files | Table preview, type detection, schema inference |
| `json` | JSON files | Formatted display, syntax highlighting |
| `image` | Image files | Inline display with original dimensions |
| `video` | Video files | HTML5 video player with controls |
| `audio` | Audio files | HTML5 audio player with controls |
| `pdf` | PDF documents | Inline PDF viewer |
| `other` | Other formats | Download option only |

---

## Size Limits

To maintain performance:

- **Text/Code files**: 5MB max (100KB content preview)
- **CSV files**: 10MB max (100 rows preview)
- **JSON files**: 5MB max
- **No limit**: Images, videos, audio, PDFs (streamed)

Files exceeding limits will show a message and download option.

---

## Testing

Run the comprehensive test suite:

```bash
./test_file_preview.sh
```

This will:
1. Create test files (SQL, CSV, JSON, Python, Text)
2. Upload them to the system
3. Test preview functionality for each format
4. Display results

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description"
}
```

**Common Errors:**
- File not found (404)
- File too large for preview
- Invalid file format
- Encoding errors for binary files

---

## Performance Considerations

1. **Caching**: Preview data is not cached by default (can be added if needed)
2. **Streaming**: Large files use streaming to avoid loading entire file into memory
3. **Limits**: Preview limits prevent server overload
4. **Lazy Loading**: Frontend should lazy-load previews when visible

---

## Security

- ✅ **File Access Control**: Previews respect file ownership
- ✅ **Path Traversal Protection**: File paths validated
- ✅ **Content Type Validation**: MIME types checked
- ✅ **Size Limits**: Prevents DOS via large files
- ✅ **Encoding Handling**: Safe handling of binary files

---

## Future Enhancements

Potential improvements:

1. **Excel Preview**: Native .xlsx preview
2. **Word Documents**: .docx preview using conversion
3. **Archive Contents**: Browse zip/tar contents
4. **Diff Viewer**: Compare file versions
5. **Markdown Rendering**: Rendered markdown preview
6. **Notebook Preview**: Jupyter notebook (.ipynb) preview
7. **More Languages**: Additional syntax highlighting
8. **Search in Preview**: Find text within previews

---

## Troubleshooting

### Problem: Preview shows "binary file" error
**Solution**: File contains non-UTF-8 characters. Use download instead.

### Problem: CSV preview truncated
**Solution**: Large CSV files only show first 100 rows. Download for full data.

### Problem: No syntax highlighting
**Solution**: Ensure frontend has syntax highlighting library (e.g., highlight.js, Prism).

### Problem: Image/video not loading
**Solution**: Check file permissions and MIME type detection.

---

## Migration Guide

### For Frontend Developers

**Old Code:**
```html
<a href="/api/download/{file_id}/">Download File</a>
```

**New Code:**
```html
<button onclick="previewFile({file_id})">Preview</button>
<button onclick="downloadFile({file_id})">Download</button>
```

### For API Users

**Old Approach:**
```python
# Always download
response = requests.get(f'/api/download/{file_id}/')
```

**New Approach:**
```python
# Get preview data first
preview = requests.get(f'/api/preview/{file_id}/').json()

if preview['can_preview']:
    # Show preview in UI
    display_preview(preview)
else:
    # Fall back to download
    response = requests.get(preview['download_url'])
```

---

## Summary

✅ **Enhanced**: Comprehensive preview support for 30+ file formats
✅ **User-Friendly**: Preview before download
✅ **Safe**: No changes to existing download functionality
✅ **Performant**: Smart size limits and streaming
✅ **Flexible**: Easy frontend integration
✅ **Tested**: Complete test suite included

Now users can preview SQL, CSV, JSON, code files, and more directly in the browser instead of downloading them!

**Get Started:**
```bash
./test_file_preview.sh
```

Enjoy the enhanced file preview experience! 🎉
