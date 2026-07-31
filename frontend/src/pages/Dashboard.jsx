import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { tracksAPI } from '../services/api';
import rybbit from '../services/rybbit';
import TrackCard from '../components/TrackCard';
import WeeklySchedule from '../components/WeeklySchedule';


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

    const track = tracks.find(t => t.id === trackId);
    try {
      await tracksAPI.delete(trackId);
      setTracks(tracks.filter(t => t.id !== trackId));
      rybbit.track('Stop Tracking Course', {
        crn: track.course.crn,
        subject: track.course.subject,
        number: track.course.course_number
      });
    } catch (err) {
      alert('Failed to remove course');
      console.error(err);
    }
  };

  const handleUpdate = async (trackId, updateData) => {
    const track = tracks.find(t => t.id === trackId);
    try {
      const response = await tracksAPI.update(trackId, updateData);
      setTracks(tracks.map(t => t.id === trackId ? response.data : t));
      rybbit.track('Update Track Settings', {
        crn: track.course.crn,
        ...updateData
      });
    } catch (err) {
      alert('Failed to update settings');
      console.error(err);
    }
  };

  /* Scroll to track logic */
  const trackRefs = useRef({});

  const handleEventClick = (trackId) => {
    const element = trackRefs.current[trackId];
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Visual feedback
      element.classList.add('ring-2', 'ring-purdue-gold', 'ring-offset-2');
      setTimeout(() => {
        element.classList.remove('ring-2', 'ring-purdue-gold', 'ring-offset-2');
      }, 1500);
    }
  };

  const openSeats = tracks.filter(t => t.course.seats_remaining > 0).length;
  const closedSeats = tracks.length - openSeats;

  return (
    <div className="page-shell">
      <div className="page-container">
        {/* Header */}
        <div className="mb-9 flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow mb-2">Fall 2026 watchlist</p>
            <h1 className="section-title">Your sections</h1>
            <p className="mt-2 text-sm text-muted">We’ll email you when any watched availability changes.</p>
          </div>
          <Link
            to="/search"

            className="btn-primary gap-2 text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Find a section
          </Link>
        </div>

        {/* Stats */}
        <div className="mb-8 grid grid-cols-3 divide-x divide-line border-y border-line">
          <div className="py-4 pr-4 sm:py-5">
            <div className="font-display text-3xl font-medium text-ink">{tracks.length}</div>
            <div className="mt-1 text-xs text-muted sm:text-sm">Watching</div>
          </div>
          <div className="px-4 py-4 sm:px-6 sm:py-5">
            <div className="font-display text-3xl font-medium text-available">{openSeats}</div>
            <div className="mt-1 text-xs text-muted sm:text-sm">Available</div>
          </div>
          <div className="py-4 pl-4 sm:py-5 sm:pl-6">
            <div className="font-display text-3xl font-medium text-muted">{closedSeats}</div>
            <div className="mt-1 text-xs text-muted sm:text-sm">Full</div>
          </div>
        </div>

        {/* Weekly Schedule */}
        {!loading && tracks.length > 0 && (
          <WeeklySchedule
            tracks={tracks}
            onEventClick={handleEventClick}
          />
        )}

        {/* Error */}
        {error && (
          <div role="alert" className="mb-6 rounded-md border border-line border-l-[3px] border-l-danger px-4 py-3 text-sm text-danger">
            {error}. <button onClick={loadTracks} className="font-semibold underline underline-offset-4">Retry</button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-ink" aria-label="Loading sections" />
          </div>
        )}

        {/* Empty state */}
        {!loading && tracks.length === 0 && (
          <div className="surface px-6 py-14 text-center sm:px-12 sm:py-16">
            <p className="eyebrow mb-3">Nothing here yet</p>
            <h2 className="font-display text-2xl font-medium text-ink">Your watchlist is empty.</h2>
            <p className="mx-auto mb-7 mt-3 max-w-sm text-sm leading-6 text-muted">
              Find the exact Purdue section you need, then watch it for availability changes.
            </p>
            <Link
              to="/search"

              className="btn-primary"
            >
              Search Courses
            </Link>
          </div>
        )}

        {/* Course grid */}
        {!loading && tracks.length > 0 && (
          <div className="surface overflow-hidden">
            {tracks.map(track => (
              <TrackCard
                key={track.id}
                ref={el => trackRefs.current[track.id] = el}
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
