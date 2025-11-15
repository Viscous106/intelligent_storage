# File Preview System - Complete Guide

## Overview

The Intelligent Storage system now includes comprehensive file preview capabilities for all file types. Users can preview files directly in the browser without downloading them.

## Supported File Types

### 1. **Images**
- **Formats**: JPG, PNG, GIF, WebP, BMP, SVG, ICO, HEIC, HEIF
- **Features**:
  - Full-size preview with zoom controls
  - Zoom in/out/reset functionality
  - Automatic thumbnail loading when available
  - Smooth image scaling

### 2. **Videos**
- **Formats**: MP4, MOV, AVI, MKV, WebM, WMV, FLV, M4V
- **Features**:
  - HTML5 video player with controls
  - Play/pause, volume control, seek
  - Fullscreen support
  - Streaming for supported formats (MP4, WebM, OGG)

### 3. **Audio**
- **Formats**: MP3, WAV, OGG, M4A, AAC, FLAC, WMA, OPUS
- **Features**:
  - HTML5 audio player
  - Play/pause, volume, seek controls
  - File metadata display
  - Clean audio interface with file info

### 4. **PDFs**
- **Formats**: PDF
- **Features**:
  - Inline PDF viewer
  - Browser-native PDF rendering
  - Scroll through pages
  - Fallback download option if browser doesn't support inline viewing

### 5. **Code Files**
- **Formats**: Python, JavaScript, TypeScript, Java, C/C++, C#, Ruby, PHP, Go, Rust, Swift, Kotlin, HTML, CSS, JSON, XML, YAML, SQL, Shell scripts
- **Features**:
  - Syntax highlighting (language-specific)
  - Line count display
  - Copy to clipboard
  - Language detection
  - Max preview size: 1MB (larger files show download option)

### 6. **Text Files**
- **Formats**: TXT, MD, LOG, CSV, RTF
- **Features**:
  - Plain text display
  - Copy to clipboard
  - Preserves formatting
  - Max preview size: 1MB

### 7. **Documents**
- **Formats**: DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, ODS, ODP
- **Features**:
  - File metadata display
  - Application suggestions for opening
  - Quick download access
  - File type and size information

### 8. **Archives**
- **Formats**: ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ
- **Features**:
  - Contents listing (first 100 files)
  - File/folder icons
  - Size information
  - Compressed vs uncompressed size (for ZIP/RAR)
  - Quick download access

### 9. **Unsupported Files**
- Any file type not listed above
- **Features**:
  - File information display
  - MIME type information
  - Download option
  - File size and extension

## Architecture

### Backend (Django)

#### API Endpoints

1. **Preview Metadata Endpoint**
   - URL: `/api/filemanager/preview/<file_path>/`
   - Method: `GET`
   - Returns: JSON with file type, preview data, URLs, metadata

2. **Content Streaming Endpoint**
   - URL: `/api/filemanager/preview/content/<file_path>/`
   - Method: `GET`
   - Returns: Raw file content with appropriate MIME type

#### Backend Files

- `backend/storage/file_preview_views.py` - Preview API views
- `backend/storage/file_manager_urls.py` - URL routing
- Functions:
  - `get_file_preview()` - Returns preview metadata based on file type
  - `get_file_content()` - Streams file content for media files
  - `get_file_type_category()` - Determines file type category
  - `detect_language()` - Detects programming language for syntax highlighting
  - `list_archive_contents()` - Extracts archive file listings

### Frontend (JavaScript + CSS)

#### JavaScript Files

- `backend/static/js/file-preview.js` - Preview modal manager
- Class: `FilePreviewManager`
  - Methods:
    - `openPreview(filePath)` - Opens preview modal
    - `closePreview()` - Closes modal
    - `renderPreview(data)` - Routes to appropriate renderer
    - `renderImagePreview()` - Image display
    - `renderVideoPreview()` - Video player
    - `renderAudioPreview()` - Audio player
    - `renderPdfPreview()` - PDF viewer
    - `renderCodePreview()` - Code display with highlighting
    - `renderTextPreview()` - Text display
    - `renderDocumentPreview()` - Document info
    - `renderArchivePreview()` - Archive contents
    - `zoomIn()` / `zoomOut()` / `resetZoom()` - Image zoom controls
    - `copyCode()` - Copy content to clipboard

#### CSS Files

- `backend/static/css/file-preview.css` - Preview modal styles
- Features:
  - Full-screen modal overlay
  - Responsive design
  - Dark theme integration
  - Smooth animations
  - Optimized for different screen sizes

#### Integration

- Updated `file-browser-pro.js` to use preview modal
- View button now opens preview instead of new tab
- Keyboard shortcut: ESC to close preview

## Usage

### For Users

1. **Open Preview**
   - Click the "👁️ View" button on any file card
   - Preview modal opens automatically

2. **Navigate Preview**
   - Use controls specific to file type (play/pause, zoom, etc.)
   - Download file from preview header
   - Press ESC or click overlay to close

3. **Image Controls**
   - Click "Zoom In" / "Zoom Out" buttons
   - Click "Reset" to restore original size

4. **Code/Text Files**
   - Click "Copy" to copy content to clipboard
   - Scroll to view entire file

### For Developers

#### Adding New File Type Support

1. **Backend**: Update `file_preview_views.py`
   ```python
   # Add extension to get_file_type_category()
   if ext in ['.new_ext']:
       return 'new_type'

   # Add preview handler in get_file_preview()
   elif file_type == 'new_type':
       preview_data['custom_field'] = 'custom_value'
   ```

2. **Frontend**: Update `file-preview.js`
   ```javascript
   // Add renderer in renderPreview()
   case 'new_type':
       this.renderNewTypePreview(container, data);
       break;

   // Add renderer method
   renderNewTypePreview(container, data) {
       container.innerHTML = `...`;
   }
   ```

3. **Styling**: Update `file-preview.css`
   ```css
   .new-type-preview {
       /* Add styles */
   }
   ```

## Dependencies

### Backend Python Packages
- `python-magic` - MIME type detection
- `rarfile` - RAR archive support (optional)
- Django built-in: `mimetypes`, `zipfile`, `tarfile`

### Frontend
- Vanilla JavaScript (ES6+)
- CSS3 with CSS variables
- No external dependencies required

## Performance Considerations

1. **File Size Limits**
   - Text/Code files: 1MB max for preview
   - Images: No limit (browser handles)
   - Videos/Audio: Streamed (no limit)
   - Archives: First 100 files shown

2. **Caching**
   - Thumbnails cached on disk
   - Browser caches previewed files
   - API responses can be cached

3. **Lazy Loading**
   - Content loaded only when preview opened
   - Media files streamed on demand
   - Archive contents extracted on-the-fly

## Security

1. **Access Control**
   - All preview endpoints require admin authentication
   - File paths validated against admin_id
   - Path traversal prevented

2. **File Safety**
   - MIME type validation
   - No code execution
   - Safe HTML escaping for text content
   - Sandboxed iframe for PDFs

## Browser Compatibility

- **Modern Browsers**: Full support (Chrome, Firefox, Safari, Edge)
- **Video/Audio**: HTML5 support required
- **PDF**: Native viewer or download option
- **Mobile**: Responsive design, touch-friendly

## Troubleshooting

### Preview Not Opening
- Check browser console for errors
- Verify file path is correct
- Ensure admin authentication is valid

### Video/Audio Not Playing
- Check file format compatibility with browser
- Verify MIME type is correct
- Try different browser

### Large Files Not Previewing
- Text/code files over 1MB show download option
- This is intentional for performance

### Archive Contents Not Showing
- Ensure archive is not corrupted
- Check that appropriate library is installed (rarfile for RAR)
- First 100 files shown for large archives

## Future Enhancements

Potential additions:
- PDF.js integration for advanced PDF features
- Syntax highlighting library (Prism.js/Highlight.js)
- Office document preview (via external service)
- Multi-file preview carousel
- Keyboard navigation between files
- Preview history/breadcrumbs
- Collaborative annotations
- Preview sharing links

## Testing

To test the preview system:

1. **Upload various file types** to your storage
2. **Click "View" button** on different file cards
3. **Test file type specific features**:
   - Images: Try zoom controls
   - Videos: Test playback
   - Code: Try copy function
   - Archives: Check contents listing
4. **Test edge cases**:
   - Very large files
   - Corrupted files
   - Unusual extensions
5. **Test on different browsers and devices**

## API Examples

### Get Preview Metadata
```bash
curl -X GET "http://localhost:8000/api/filemanager/preview/photos/admin123_image.jpg"
```

Response:
```json
{
  "success": true,
  "file_type": "image",
  "name": "admin123_image.jpg",
  "size": 2048576,
  "size_human": "2.0 MB",
  "extension": ".jpg",
  "mime_type": "image/jpeg",
  "preview_url": "/api/filemanager/preview/content/photos/admin123_image.jpg",
  "download_url": "/api/filemanager/download/photos/admin123_image.jpg",
  "thumbnails": {
    "small": "/api/filemanager/thumbnail/photos/admin123_image.jpg?size=small",
    "medium": "/api/filemanager/thumbnail/photos/admin123_image.jpg?size=medium",
    "large": "/api/filemanager/thumbnail/photos/admin123_image.jpg?size=large"
  }
}
```

### Stream File Content
```bash
curl -X GET "http://localhost:8000/api/filemanager/preview/content/videos/admin123_video.mp4" > video.mp4
```

## License

Part of the Intelligent Storage system.
