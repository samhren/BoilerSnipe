import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { tracksAPI } from '../services/api';
import TrackCard from '../components/TrackCard';

const Dashboard = () => {
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTracks();
  }, []);

  const loadTracks = async () => {
    try {
      setLoading(true);
      const response = await tracksAPI.getAll();
      setTracks(response.data);
      setError('');
    } catch (err) {
      setError('Failed to load tracked courses');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (trackId) => {
    if (!confirm('Stop tracking this course?')) {
      return;
    }

    try {
      await tracksAPI.delete(trackId);
      setTracks(tracks.filter(t => t.id !== trackId));
    } catch (err) {
      alert('Failed to remove course');
      console.error(err);
    }
  };

  const handleUpdate = async (trackId, updateData) => {
    try {
      const response = await tracksAPI.update(trackId, updateData);
      setTracks(tracks.map(t => t.id === trackId ? response.data : t));
    } catch (err) {
      alert('Failed to update settings');
      console.error(err);
    }
  };

  const openSeats = tracks.filter(t => t.course.seats_remaining > 0).length;
  const closedSeats = tracks.length - openSeats;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-800">Dashboard</h1>
            <p className="text-slate-500 text-sm sm:text-base mt-1">Track your courses and get notified</p>
          </div>
          <Link
            to="/search"
            className="inline-flex items-center justify-center gap-2 bg-slate-800 text-white px-4 py-2.5 rounded-lg font-medium hover:bg-slate-700 transition-colors text-sm sm:text-base"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Course
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 sm:gap-4 mb-6 sm:mb-8">
          <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200">
            <div className="text-2xl sm:text-3xl font-bold text-slate-800">{tracks.length}</div>
            <div className="text-slate-500 text-xs sm:text-sm mt-1">Tracking</div>
          </div>
          <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200">
            <div className="text-2xl sm:text-3xl font-bold text-emerald-600">{openSeats}</div>
            <div className="text-slate-500 text-xs sm:text-sm mt-1">Available</div>
          </div>
          <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200">
            <div className="text-2xl sm:text-3xl font-bold text-slate-400">{closedSeats}</div>
            <div className="text-slate-500 text-xs sm:text-sm mt-1">Full</div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin"></div>
          </div>
        )}

        {/* Empty state */}
        {!loading && tracks.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-8 sm:p-12 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-slate-800 mb-2">No courses tracked</h2>
            <p className="text-slate-500 text-sm mb-6 max-w-sm mx-auto">
              Start tracking courses to get notified when seats become available
            </p>
            <Link
              to="/search"
              className="inline-flex items-center gap-2 bg-slate-800 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-slate-700 transition-colors"
            >
              Search Courses
            </Link>
          </div>
        )}

        {/* Course grid */}
        {!loading && tracks.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {tracks.map(track => (
              <TrackCard
                key={track.id}
                track={track}
                onDelete={handleDelete}
                onUpdate={handleUpdate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
