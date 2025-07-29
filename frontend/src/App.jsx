// src/App.jsx
import React, { useState } from "react";
import FileUploader from "./components/FileUploader";
import ProgressStepper from "./components/ProgressStepper";
import Loader from "./components/Loader";

export default function App() {
  const [progress, setProgress] = useState([]);    // [{ name, status, url }]
  const [loading, setLoading] = useState(false);

  const handleUpload = async (files) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    setLoading(true);
    setProgress(files.map((f) => ({ name: f.name, status: "Uploading", url: null })));

    try {
      const res = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();  // [{ id, pdf_url }, ...]

      const updated = data.map((item, idx) => ({
        name: files[idx].name,        // original filename
        status: "Ready",
        url: `http://localhost:8000${item.pdf_url}`,
      }));
      setProgress(updated);
    } catch (err) {
      console.error("Upload failed:", err);
      setProgress(files.map((f) => ({ name: f.name, status: "Failed", url: null })));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ui-container relative">
      {loading && <Loader />}

      <h1 className="ui-heading">Resume Consolidator</h1>
      <br /><br />
      <FileUploader onUpload={handleUpload} />

      <ProgressStepper steps={progress} />
    </div>
  );
}
