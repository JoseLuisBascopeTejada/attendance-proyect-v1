import { useState, type FormEvent } from 'react';
import { apiClient } from '../api/client';
import { WebcamCapture } from '../components/WebcamCapture';

function base64ToBlob(base64: string): Blob {
  const [header, data] = base64.split(',');
  const mime = header.match(/:(.*?);/)?.[1] ?? 'image/jpeg';
  const binary = atob(data);
  const array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    array[i] = binary.charCodeAt(i);
  }
  return new Blob([array], { type: mime });
}

export function Register() {
  const [name, setName] = useState('');
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<{ id: number; name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !capturedImage) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const blob = base64ToBlob(capturedImage);
      const formData = new FormData();
      formData.append('file', blob, 'photo.jpg');
      formData.append('name', name.trim());

      const response = await apiClient.post('/register', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setSuccess({ id: response.data.id, name: response.data.name });
      setName('');
      setCapturedImage(null);
    } catch (err: unknown) {
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'status' in err.response
      ) {
        const status = err.response.status as number;
        const detail = (err.response as { data?: { detail?: string } }).data?.detail;

        if (status === 400) {
          setError(detail ?? 'No face detected. Please try again with a clear face.');
        } else if (status === 413) {
          setError(detail ?? 'Image is too large or has excessive dimensions.');
        } else {
          setError(detail ?? 'Registration failed. Please try again.');
        }
      } else {
        setError('Network error. Is the backend running?');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '32px 20px' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8, color: 'var(--text-h)' }}>
        Register Student
      </h1>
      <p style={{ color: 'var(--text)', marginBottom: 24 }}>
        Enter a name and capture a photo to register a new student.
      </p>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 20 }}>
          <label
            htmlFor="student-name"
            style={{ display: 'block', fontSize: 14, fontWeight: 600, marginBottom: 6, color: 'var(--text-h)' }}
          >
            Student Name
          </label>
          <input
            id="student-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Juan Perez"
            required
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 8,
              border: '1px solid var(--border)',
              fontSize: 15,
              background: 'var(--bg)',
              color: 'var(--text-h)',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <WebcamCapture onCapture={setCapturedImage} />
        </div>

        {capturedImage && (
          <div style={{ marginBottom: 20, textAlign: 'center' }}>
            <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: 'var(--text-h)' }}>
              Captured Photo
            </p>
            <img
              src={capturedImage}
              alt="Captured"
              style={{
                maxWidth: 320,
                borderRadius: 8,
                border: '1px solid var(--border)',
              }}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !name.trim() || !capturedImage}
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: 8,
            border: 'none',
            background: loading || !name.trim() || !capturedImage ? '#999' : 'var(--accent)',
            color: '#fff',
            fontSize: 16,
            fontWeight: 600,
            cursor: loading || !name.trim() || !capturedImage ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Registering...' : 'Register Student'}
        </button>
      </form>

      {loading && (
        <div style={{ textAlign: 'center', marginTop: 16, color: 'var(--text)' }}>
          <div
            style={{
              display: 'inline-block',
              width: 24,
              height: 24,
              border: '3px solid var(--border)',
              borderTopColor: 'var(--accent)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <span style={{ marginLeft: 8 }}>Processing...</span>
        </div>
      )}

      {success && (
        <div
          style={{
            marginTop: 16,
            padding: '12px 16px',
            borderRadius: 8,
            background: '#d4edda',
            border: '1px solid #28a745',
            color: '#155724',
          }}
        >
          Registered <strong>{success.name}</strong> (ID: {success.id})
        </div>
      )}

      {error && (
        <div
          style={{
            marginTop: 16,
            padding: '12px 16px',
            borderRadius: 8,
            background: '#f8d7da',
            border: '1px solid #dc3545',
            color: '#721c24',
          }}
        >
          {error}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
