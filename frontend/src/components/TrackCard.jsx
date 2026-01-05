const TrackCard = ({ track, onDelete, onUpdate }) => {
  const { course } = track;
  const isUpdating = course.seats_capacity === 0 && course.seats_remaining === 0;

  const getStatusStyles = () => {
    if (isUpdating) return { bg: 'bg-slate-300', text: 'text-slate-600', label: 'Updating...' };
    if (course.seats_remaining > 5) return { bg: 'bg-emerald-500', text: 'text-white', label: 'Available' };
    if (course.seats_remaining > 0) return { bg: 'bg-amber-500', text: 'text-white', label: 'Limited' };
    return { bg: 'bg-slate-400', text: 'text-white', label: 'Full' };
  };

  const status = getStatusStyles();

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:border-slate-300 transition-all hover:shadow-md">
      {/* Header with status */}
      <div className={`${status.bg} px-4 py-2 flex justify-between items-center`}>
        <span className={`text-sm font-medium ${status.text}`}>{status.label}</span>
        {!isUpdating && (
          <span className={`text-sm font-bold ${status.text}`}>
            {course.seats_remaining}/{course.seats_capacity} seats
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

        {/* Notification toggles */}
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

        <button
          onClick={() => onDelete(track.id)}
          className="w-full mt-4 py-2 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          Remove
        </button>
      </div>
    </div>
  );
};

export default TrackCard;
