const CourseCard = ({ course, onTrack, isTracking, isTracked }) => {
  const isUntracked = course.seats_capacity === 0 && course.seats_remaining === 0;

  const getStatusStyles = () => {
    if (isUntracked) return { bg: 'bg-slate-100', text: 'text-slate-500', label: 'Not checked' };
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
        {!isUntracked && (
          <span className={`text-sm font-bold ${status.text}`}>
            {Math.max(0, course.seats_remaining)}/{course.seats_capacity}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-lg font-semibold text-slate-800">{course.course_code}</h3>
            {course.schedule_type && (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                {course.schedule_type}
              </span>
            )}
          </div>
          <p className="text-slate-600 text-sm line-clamp-1">{course.title}</p>
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
            <span className="text-slate-700 truncate">{course.instructor || 'TBA'}</span>
          </div>
        </div>

        <button
          onClick={() => onTrack(course.crn)}
          disabled={isTracking || isTracked}
          className={`w-full py-2.5 rounded-lg font-medium text-sm transition-colors ${isTracked
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
              : isTracking
                ? 'bg-slate-200 text-slate-500 cursor-wait'
                : 'bg-slate-800 text-white hover:bg-slate-700'
            }`}
        >
          {isTracking ? 'Adding...' : isTracked ? 'Tracking' : 'Track Course'}
        </button>
      </div>
    </div>
  );
};

export default CourseCard;
