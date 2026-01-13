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
  const instructorRecords = grades?.records?.filter(
    r => instructor && r.instructor?.toLowerCase().includes(instructor.toLowerCase().split(',')[0])
  ) || [];

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
            <div className="space-y-4">
              {/* Course-wide averages */}
              <div>
                <p className="text-xs text-slate-400 mb-2">
                  Based on {grades.total_sections} sections across {grades.semesters?.length || 0} semesters
                </p>
                <div className="space-y-1">
                  {/* A grades */}
                  <div className="flex items-center gap-1">
                    <span className="w-5 text-xs font-medium text-slate-500">A</span>
                    <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden flex">
                      {grades.avg_a_plus > 0 && (
                        <div className="h-full bg-emerald-600" style={{ width: `${(grades.avg_a_plus || 0) * 100}%` }} title={`A+: ${((grades.avg_a_plus || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_a_base > 0 && (
                        <div className="h-full bg-emerald-500" style={{ width: `${(grades.avg_a_base || 0) * 100}%` }} title={`A: ${((grades.avg_a_base || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_a_minus > 0 && (
                        <div className="h-full bg-emerald-400" style={{ width: `${(grades.avg_a_minus || 0) * 100}%` }} title={`A-: ${((grades.avg_a_minus || 0) * 100).toFixed(1)}%`} />
                      )}
                    </div>
                    <span className="w-12 text-xs text-slate-600 text-right">{((grades.avg_a || 0) * 100).toFixed(1)}%</span>
                  </div>
                  {/* B grades */}
                  <div className="flex items-center gap-1">
                    <span className="w-5 text-xs font-medium text-slate-500">B</span>
                    <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden flex">
                      {grades.avg_b_plus > 0 && (
                        <div className="h-full bg-lime-600" style={{ width: `${(grades.avg_b_plus || 0) * 100}%` }} title={`B+: ${((grades.avg_b_plus || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_b_base > 0 && (
                        <div className="h-full bg-lime-500" style={{ width: `${(grades.avg_b_base || 0) * 100}%` }} title={`B: ${((grades.avg_b_base || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_b_minus > 0 && (
                        <div className="h-full bg-lime-400" style={{ width: `${(grades.avg_b_minus || 0) * 100}%` }} title={`B-: ${((grades.avg_b_minus || 0) * 100).toFixed(1)}%`} />
                      )}
                    </div>
                    <span className="w-12 text-xs text-slate-600 text-right">{((grades.avg_b || 0) * 100).toFixed(1)}%</span>
                  </div>
                  {/* C grades */}
                  <div className="flex items-center gap-1">
                    <span className="w-5 text-xs font-medium text-slate-500">C</span>
                    <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden flex">
                      {grades.avg_c_plus > 0 && (
                        <div className="h-full bg-amber-600" style={{ width: `${(grades.avg_c_plus || 0) * 100}%` }} title={`C+: ${((grades.avg_c_plus || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_c_base > 0 && (
                        <div className="h-full bg-amber-500" style={{ width: `${(grades.avg_c_base || 0) * 100}%` }} title={`C: ${((grades.avg_c_base || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_c_minus > 0 && (
                        <div className="h-full bg-amber-400" style={{ width: `${(grades.avg_c_minus || 0) * 100}%` }} title={`C-: ${((grades.avg_c_minus || 0) * 100).toFixed(1)}%`} />
                      )}
                    </div>
                    <span className="w-12 text-xs text-slate-600 text-right">{((grades.avg_c || 0) * 100).toFixed(1)}%</span>
                  </div>
                  {/* D grades */}
                  <div className="flex items-center gap-1">
                    <span className="w-5 text-xs font-medium text-slate-500">D</span>
                    <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden flex">
                      {grades.avg_d_plus > 0 && (
                        <div className="h-full bg-orange-600" style={{ width: `${(grades.avg_d_plus || 0) * 100}%` }} title={`D+: ${((grades.avg_d_plus || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_d_base > 0 && (
                        <div className="h-full bg-orange-500" style={{ width: `${(grades.avg_d_base || 0) * 100}%` }} title={`D: ${((grades.avg_d_base || 0) * 100).toFixed(1)}%`} />
                      )}
                      {grades.avg_d_minus > 0 && (
                        <div className="h-full bg-orange-400" style={{ width: `${(grades.avg_d_minus || 0) * 100}%` }} title={`D-: ${((grades.avg_d_minus || 0) * 100).toFixed(1)}%`} />
                      )}
                    </div>
                    <span className="w-12 text-xs text-slate-600 text-right">{((grades.avg_d || 0) * 100).toFixed(1)}%</span>
                  </div>
                  {/* F grade */}
                  <GradeBar label="F" percentage={grades.avg_f} color="bg-red-500" />
                  {grades.avg_w > 0.01 && (
                    <GradeBar label="W" percentage={grades.avg_w} color="bg-slate-400" />
                  )}
                </div>
              </div>

              {/* Instructor-specific data if available */}
              {instructorRecords.length > 0 && (
                <div className="pt-2 border-t border-slate-50">
                  <p className="text-xs font-medium text-slate-600 mb-2">
                    This Instructor ({instructorRecords.length} sections)
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

                      return (
                        <>
                          <GradeBar label="A" percentage={avgA} color="bg-emerald-500" />
                          <GradeBar label="B" percentage={avgB} color="bg-lime-500" />
                          <GradeBar label="C" percentage={avgC} color="bg-amber-500" />
                          <GradeBar label="D" percentage={avgD} color="bg-orange-500" />
                          <GradeBar label="F" percentage={avgF} color="bg-red-500" />
                        </>
                      );
                    })()}
                  </div>
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

        {/* Grade Distribution Section */}
        <GradeSection courseCode={course.course_code} instructor={course.instructor} />

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
