import React, { useState } from 'react';

export default function PdfUpload() {
  const [message, setMessage] = useState('');
  
  const handleUpload = (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('file', e.target.files[0]);
    
    fetch('/api/pdf/upload', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        setMessage(`Error: ${data.error}`);
      } else {
        setMessage(`Success: ${data.message}`);
      }
    })
    .catch(error => {
      setMessage(`Error: ${error.message}`);
    });
  };
  
  return (
    <div className="pdf-upload">
      <h3>Upload PDF</h3>
      <input type="file" accept=".pdf" onChange={handleUpload} />
      {message && <p>{message}</p>}
      <p className="hint">Supported formats: PDF/A, standard PDF (max 10MB)</p>
    </div>
  );
}