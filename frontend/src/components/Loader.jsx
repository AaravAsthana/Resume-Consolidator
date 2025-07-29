// src/components/Loader.jsx
import React from "react";

export default function Loader() {
  return (
    <div className="banter-loader">
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} className="banter-loader__box" />
      ))}
    </div>
  );
}
