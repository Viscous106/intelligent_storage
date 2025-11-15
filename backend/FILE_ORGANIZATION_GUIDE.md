# File Organization & Admin Access Guide

## ✅ Admin User Created

**Admin Credentials:**
- **Username:** `Viscous106`
- **Password:** `787898`
- **Admin URL:** http://localhost:8000/admin/

---

## 📁 Organized File Storage

Your uploaded files are now automatically organized by type!

### Folder Structure

```
media/
├── images/          # 🖼️  All image files (jpg, png, gif, etc.)
│   └── 2025/
│       └── 11/
│           └── your_image.jpg
├── videos/          # 🎬  All video files (mp4, avi, mov, etc.)
│   └── 2025/
│       └── 11/
│           └── your_video.mp4
├── audio/           # 🎵  All audio files (mp3, wav, flac, etc.)
│   └── 2025/
│       └── 11/
│           └── your_audio.mp3
├── documents/       # 📄  All documents (pdf, docx, xlsx, etc.)
│   └── 2025/
│       └── 11/
│           └── your_document.pdf
├── code/            # 💻  All code files (py, js, etc.)
│   └── 2025/
│       └── 11/
│           └── your_script.py
├── compressed/      # 📦  All archives (zip, rar, tar.gz, etc.)
│   └── 2025/
│       └── 11/
│           └── your_archive.zip
└── others/          # 📎  Other file types
    └── 2025/
        └── 11/
            └── other_file.dat
```

**Features:**
- ✅ **Automatic categorization** by file type
- ✅ **Date-based organization** (Year/Month folders)
- ✅ **Unique filenames** (prevents overwrites)
- ✅ **Cross-platform** (Works on Windows & Linux)

---

## 🌐 Browse Your Files

### Web Interface
Visit: **http://localhost:8000/files/browse/**

**Features:**
- 📁 Browse by category (Images, Videos, Documents, etc.)
- 🔍 Search files
- 👁️ Preview files
- ⬇️ Download files
- 📊 View storage statistics

### API Endpoints

#### 1. Browse Files by Category
```bash
# Get all images
GET http://localhost:8000/files/api/browse/?category=image

# Get all videos
GET http://localhost:8000/files/api/browse/?category=video

# Get all documents
GET http://localhost:8000/files/api/browse/?category=document

# Get all files
GET http://localhost:8000/files/api/browse/?category=all
```

#### 2. Get Storage Statistics
```bash
GET http://localhost:8000/files/api/stats/
```

**Response:**
```json
{
  "by_type": {
    "image": {
      "count": 15,
      "size_bytes": 5242880,
      "size_mb": 5.00,
      "folder": "images"
    },
    "video": {
      "count": 3,
      "size_bytes": 104857600,
      "size_mb": 100.00,
      "folder": "videos"
    }
    // ... more types
  },
  "total": {
    "count": 50,
    "size_bytes": 524288000,
    "size_mb": 500.00
  }
}
```

#### 3. Download a File
```bash
GET http://localhost:8000/files/api/download/<file_id>/
```

#### 4. Preview a File (Images, PDFs)
```bash
GET http://localhost:8000/files/api/preview/<file_id>/
```

---

## 📤 Upload Files

Files are automatically organized when uploaded!

### Using Admin Interface
1. Go to http://localhost:8000/admin/
2. Login with `Viscous106` / `787898`
3. Go to "Media files" → "Add media file"
4. Upload file
5. **File is automatically organized by type!**

### Using API
```bash
# Upload a file (it will be auto-organized)
POST http://localhost:8000/api/upload/file/
Content-Type: multipart/form-data

file: <your file>
```

**What happens:**
1. File type is detected (image, video, document, etc.)
2. File is stored in the correct category folder
3. Date-based subfolder is created (2025/11/)
4. Unique filename is generated
5. File path is saved in database

---

## 🔍 Admin Dashboard Features

### Login to Admin Panel
```
URL: http://localhost:8000/admin/
Username: Viscous106
Password: 787898
```

### What You Can Do

#### 1. **View All Files**
- See all uploaded files
- Filter by type (images, videos, documents)
- Search by name
- View file details
- Download files

#### 2. **Manage File Search Stores**
- Create document stores
- Configure chunking strategies
- Set storage quotas
- View usage statistics

#### 3. **Browse Document Chunks**
- View text chunks from indexed documents
- See embeddings
- Check token counts

#### 4. **View Search History**
- See all search queries
- Result counts
- Popular searches

#### 5. **Monitor Storage**
- Total files uploaded
- Storage usage by type
- Quota usage
- File statistics

---

## 📊 File Organization Features

### Automatic Features
✅ **Type Detection** - Detects file type automatically
✅ **Smart Organization** - Organizes by type and date
✅ **Unique Names** - Prevents filename conflicts
✅ **Metadata Tracking** - Stores file information
✅ **Cross-Platform** - Works on Windows & Linux

### File Type Categories
- 🖼️ **Images:** JPG, PNG, GIF, SVG, WebP, etc.
- 🎬 **Videos:** MP4, AVI, MOV, MKV, WebM, etc.
- 🎵 **Audio:** MP3, WAV, FLAC, AAC, OGG, etc.
- 📄 **Documents:** PDF, DOCX, XLSX, PPTX, TXT, etc.
- 💻 **Code:** PY, JS, HTML, CSS, Java, etc.
- 📦 **Compressed:** ZIP, RAR, 7Z, TAR.GZ, etc.
- 📎 **Others:** Any other file types

---

## 🔧 Management Commands

### Check Storage Stats
```bash
./run.sh quotas
```

### Browse Files by Type (Command Line)
```bash
# List all images
ls -la media/images/

# List all videos
ls -la media/videos/

# List all documents
ls -la media/documents/
```

### Clean Up Orphaned Files
```bash
./run.sh cleanup
```

---

## 🎯 Quick Reference

| Task | Command/URL |
|------|-------------|
| **Admin Login** | http://localhost:8000/admin/ |
| **Browse Files** | http://localhost:8000/files/browse/ |
| **View Stats** | http://localhost:8000/files/api/stats/ |
| **Download File** | http://localhost:8000/files/api/download/{id}/ |
| **Upload File** | POST to /api/upload/file/ |
| **Admin Username** | `Viscous106` |
| **Admin Password** | `787898` |

---

## 📁 Example: Where Files Are Stored

When you upload:
- `photo.jpg` → `media/images/2025/11/photo.jpg`
- `video.mp4` → `media/videos/2025/11/video.mp4`
- `report.pdf` → `media/documents/2025/11/report.pdf`
- `song.mp3` → `media/audio/2025/11/song.mp3`
- `archive.zip` → `media/compressed/2025/11/archive.zip`

**All organized automatically!** 🎉

---

## 🚀 Next Steps

1. **Login to Admin:** http://localhost:8000/admin/
2. **Upload some files** via admin interface
3. **Browse your files:** http://localhost:8000/files/browse/
4. **Check stats:** http://localhost:8000/files/api/stats/

Everything is ready to use! Your files will be automatically organized by type and date.
