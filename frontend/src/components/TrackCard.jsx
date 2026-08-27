import React, { forwardRef } from 'react';
import { Link } from 'react-router-dom';

const formatDelistedDate = (value) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

const TrackCard = forwardRef(({ track, onDelete, onUpdate }, ref) => {
  const { course } = track;

  // Purdue has removed this section from the schedule, so the sniper has
  // stopped checking it. Its seat numbers are frozen at whatever they were the
  // last time the section existed, and showing them as though they were live is
  // the thing this state exists to prevent.
  const isCancelled = course.is_listed === false;
  const isUpdating = !isCancelled && course.seats_capacity === 0 && course.seats_remaining === 0;
  const delistedOn = formatDelistedDate(course.delisted_at);

  const getStatusStyles = () => {
    if (isCancelled) return { bg: 'bg-red-600', text: 'text-white', label: 'Section cancelled' };
    if (isUpdating) return { bg: 'bg-slate-300', text: 'text-slate-600', label: 'Updating...' };
    if (course.seats_remaining > 5) return { bg: 'bg-emerald-500', text: 'text-white', label: 'Available' };
    if (course.seats_remaining > 0) return { bg: 'bg-amber-500', text: 'text-white', label: 'Limited' };
    return { bg: 'bg-slate-400', text: 'text-white', label: 'Full' };
  };

  const status = getStatusStyles();

  return (
    <div
      ref={ref}
      className={`bg-white rounded-xl overflow-hidden transition-all scroll-mt-24 duration-500 ${
        isCancelled
          ? 'border-2 border-red-300 hover:border-red-400 hover:shadow-md'
          : 'border border-slate-200 hover:border-slate-300 hover:shadow-md'
      }`}
    >
      {/* Header with status */}
      <div className={`${status.bg} px-4 py-2 flex justify-between items-center gap-2`}>
        <span className={`text-sm font-semibold ${status.text} flex items-center gap-1.5`}>
          {isCancelled && (
            <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
          )}
          {status.label}
        </span>
        {/* No seat count for a cancelled section. There is nothing live to show. */}
        {!isUpdating && !isCancelled && (
          <span className={`text-sm font-bold ${status.text}`}>
            {Math.max(0, course.seats_remaining)}/{course.seats_capacity} seats
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold text-slate-800">{course.course_code}</h3>
              {course.schedule_type && (
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                  {course.schedule_type}
                </span>
              )}
            </div>
            <p className="text-slate-600 text-sm">{course.title}</p>
          </div>
        </div>

        {isCancelled && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm font-semibold text-red-800 mb-1">
              No longer offered
            </p>
            <p className="text-sm text-red-700">
              Purdue removed this section from the schedule
              {delistedOn ? ` on ${delistedOn}` : ''}. We have stopped checking it,
              so <strong>you will not get any alerts for this CRN</strong>.
            </p>
            {course.seats_capacity > 0 && (
              <p className="text-xs text-red-600/90 mt-2">
                Last known before it was removed
                {delistedOn ? ` on ${delistedOn}` : ''}:{' '}
                {Math.max(0, course.seats_remaining)}/{course.seats_capacity} seats.
                These numbers are not live.
              </p>
            )}
          </div>
        )}

        <div className="space-y-1.5 text-sm mb-4">
          <div className="flex">
            <span className="text-slate-400 w-20">CRN</span>
            <span className="text-slate-700 font-mono">{course.crn}</span>
          </div>
          <div className="flex">
            <span className="text-slate-400 w-20">Time</span>
            <span className="text-slate-700">{course.time || 'TBA'} {course.days && `(${course.days})`}</span>
          </div>
          <div className="flex">
            <span className="text-slate-400 w-20">Instructor</span>
            <span className="text-slate-700">{course.instructor || 'TBA'}</span>
          </div>
        </div>

        {/* Notification toggles. A cancelled section has nothing to notify on,
            so offering working switches would be a lie. */}
        {!isCancelled && (
          <div className="border-t border-slate-100 pt-3 space-y-2">
            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-sm text-slate-600 group-hover:text-slate-800">Notify on open</span>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={track.notify_on_open}
                  onChange={(e) => onUpdate(track.id, { notify_on_open: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-200 rounded-full peer peer-checked:bg-amber-500 transition-colors"></div>
                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow peer-checked:translate-x-4 transition-transform"></div>
              </div>
            </label>

            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-sm text-slate-600 group-hover:text-slate-800">Notify on close</span>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={track.notify_on_close}
                  onChange={(e) => onUpdate(track.id, { notify_on_close: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-200 rounded-full peer peer-checked:bg-amber-500 transition-colors"></div>
                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow peer-checked:translate-x-4 transition-transform"></div>
              </div>
            </label>
          </div>
        )}

        {isCancelled ? (
          // Finding a replacement is the constructive next step, so it leads.
          // Removing is still one click away, styled like every other Remove.
          <div className="flex gap-2 mt-4">
            <Link
              to="/search"
              className="flex-1 py-2 text-sm text-center font-medium text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              Find another section
            </Link>
            <button
              onClick={() => onDelete(track.id)}
              className="flex-1 py-2 text-sm font-medium text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              Remove
            </button>
          </div>
        ) : (
          <button
            onClick={() => onDelete(track.id)}
            className="w-full mt-4 py-2 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            Remove
          </button>
        )}
      </div>
    </div>
  );
});

TrackCard.displayName = 'TrackCard';

export default TrackCard;
