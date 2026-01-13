import { useState } from 'react';
import { gradesAPI } from '../services/api';

const GradeBar = ({ label, percentage, color }) => {
  const pct = percentage ? (percentage * 100).toFixed(1) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-6 text-xs font-medium text-slate-500">{label}</span>
      <div className="flex-1 h-4 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-12 text-xs text-slate-600 text-right">{pct}%</span>
    </div>
  );
};

const GradeSection = ({ courseCode, instructor }) => {
  const [expanded, setExpanded] = useState(false);
  const [grades, setGrades] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleToggle = async () => {
    if (!expanded && !grades) {
      setLoading(true);
      setError(null);
      try {
        const response = await gradesAPI.getByCourseCode(courseCode);
        setGrades(response.data);
      } catch (err) {
        if (err.response?.status === 404) {
          setError('No grade data available');
        } else {
          setError('Failed to load grades');
        }
      } finally {
        setLoading(false);
      }
    }
    setExpanded(!expanded);
  };

  // Filter records for current instructor if available
  const instructorRecords = grades?.records?.filter(r => {
    if (!instructor) return false;
    // Handle "Firstname Lastname" format from website vs "Lastname, Firstname" in grades
    // Also handle potential comma-separated list of instructors by taking the first one
    const primaryName = instructor.split(',')[0].trim().toLowerCase();
    const nameParts = primaryName.split(' ').filter(p => p.trim());
    if (nameParts.length === 0) return false;

    const lastName = nameParts[nameParts.length - 1];
    const recordName = r.instructor?.toLowerCase() || '';

    // Record must contain the last name
    if (!recordName.includes(lastName)) return false;

    // If we have a first name, it should also be present to avoid false positives (e.g. Smith)
    if (nameParts.length > 1) {
      const firstName = nameParts[0];
      return recordName.includes(firstName);
    }

    return true;
  }) || [];

  return (
    <div className="border-t border-slate-100 mt-3">
      <button
        onClick={handleToggle}
        className="w-full py-2 flex items-center justify-between text-sm text-slate-500 hover:text-slate-700 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Grade Distribution
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="pb-3">
          {loading && (
            <div className="flex justify-center py-4">
              <div className="w-5 h-5 border-2 border-slate-200 border-t-slate-500 rounded-full animate-spin" />
            </div>
          )}

          {error && (
            <p className="text-sm text-slate-400 py-2 text-center">{error}</p>
          )}


          {grades && !error && (
            <div className="space-y-3">
              {/* Instructor-specific data - shown first if available */}
              {instructorRecords.length > 0 ? (
                <div>
                  <p className="text-xs text-slate-500 mb-2">
                    {instructor?.split(',')[0]} ({instructorRecords.length} {instructorRecords.length === 1 ? 'section' : 'sections'})
                  </p>
                  <div className="space-y-1.5">
                    {(() => {
                      const avgA = instructorRecords.reduce((sum, r) =>
                        sum + (r.grade_a_plus || 0) + (r.grade_a || 0) + (r.grade_a_minus || 0), 0) / instructorRecords.length;
                      const avgB = instructorRecords.reduce((sum, r) =>
                        sum + (r.grade_b_plus || 0) + (r.grade_b || 0) + (r.grade_b_minus || 0), 0) / instructorRecords.length;
                      const avgC = instructorRecords.reduce((sum, r) =>
                        sum + (r.grade_c_plus || 0) + (r.grade_c || 0) + (r.grade_c_minus || 0), 0) / instructorRecords.length;
                      const avgD = instructorRecords.reduce((sum, r) =>
                        sum + (r.grade_d_plus || 0) + (r.grade_d || 0) + (r.grade_d_minus || 0), 0) / instructorRecords.length;
                      const avgF = instructorRecords.reduce((sum, r) =>
                        sum + (r.grade_e || 0) + (r.grade_f || 0), 0) / instructorRecords.length;
                      const avgW = instructorRecords.reduce((sum, r) =>
                        sum + (r.grade_w || 0), 0) / instructorRecords.length;

                      return (
                        <>
                          <GradeBar label="A" percentage={avgA} color="bg-emerald-500" />
                          <GradeBar label="B" percentage={avgB} color="bg-lime-500" />
                          <GradeBar label="C" percentage={avgC} color="bg-amber-500" />
                          <GradeBar label="D" percentage={avgD} color="bg-orange-500" />
                          <GradeBar label="F" percentage={avgF} color="bg-red-500" />
                          {avgW > 0.01 && <GradeBar label="W" percentage={avgW} color="bg-slate-400" />}
                        </>
                      );
                    })()}
                  </div>
                </div>
              ) : (
                <div className="py-2 text-center text-xs text-slate-400">
                  No grade data available for this instructor
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const CourseCard = ({ course, onTrack, isTracking, isTracked }) => {
  const isUntracked = course.seats_remaining === 999;

  const getStatusStyles = () => {
    if (isUntracked) return { bg: 'bg-slate-100', text: 'text-slate-500', label: 'Untracked' };
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

        {/* Grade Distribution Section - Only show for Lecture sections */}
        {course.schedule_type === 'Lecture' && (
          <GradeSection courseCode={course.course_code} instructor={course.instructor} />
        )}

        <button
          onClick={() => onTrack(course.crn)}
          disabled={isTracking || isTracked}
          className={`w-full py-2.5 rounded-lg font-medium text-sm transition-colors mt-3 ${isTracked
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
