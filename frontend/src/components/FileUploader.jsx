// src/components/FileUploader.jsx
import React, { useCallback } from "react";

export default function FileUploader({ onUpload }) {
  const onFileChange = useCallback((e) => {
    const files = Array.from(e.target.files);
    onUpload(files);
  }, [onUpload]);

  return (
    <form className="file-upload-form ui-uploader">
      <label htmlFor="file" className="file-upload-label">
        <div className="file-upload-design">
          <svg viewBox="0 0 640 512" height="1em">
            <path d="M144 480C64.5 480 0 415.5 0 336c0-62.8 …"></path>
          </svg>
          <p>Drag and Drop</p>
          <p>or</p>
          <span className="browse-button">Browse file</span>
        </div>
        <input
          id="file"
          type="file"
          multiple
          onChange={onFileChange}
        />
      </label>
    </form>
  );
}
