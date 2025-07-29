// src/components/ProgressStepper.jsx
import React from "react";

export default function ProgressStepper({ steps }) {
  return (
    <div className="ui-progress">
      {steps.map((s, idx) => (
        <div key={idx} className="ui-progress-item">
          <div>
            <p className="font-medium">{s.name}</p>
            <p className="text-sm text-gray-600">{s.status}</p>
          </div>
          {s.url && (
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="ui-download-btn"
            >
              Download
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
