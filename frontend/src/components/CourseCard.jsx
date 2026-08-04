import { useState } from 'react';
import { gradesAPI } from '../services/api';

const StackedGradeBar = ({ data }) => {
  // Filter out zero values and normalize to 100% just in case
  const validSegments = data.filter(d => d.value > 0);
  const total = validSegments.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="w-full mb-6">
      <div className="h-4 w-full flex rounded-md overflow-visible bg-slate-100">
        {validSegments.map((segment, index) => {
          const width = total > 0 ? (segment.value / total) * 100 : 0;

          return (
            <div
              key={index}
              className={`${segment.color} h-full relative group first:rounded-l-md last:rounded-r-md transition-all duration-300 hover:brightness-110`}
              style={{ width: `${width}%` }}
            >
              {/* Label directly under the bar - distinct from tooltip */}
              {width > 3 && (
                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 flex flex-col items-center">
                  <span className="text-[9px] font-bold text-slate-700 whitespace-nowrap leading-none">
                    {segment.label}
                  </span>
                  <span className="text-[8px] text-slate-500 whitespace-nowrap leading-none mt-0.5">
                    {(segment.value * 100).toFixed(0)}%
                  </span>
                </div>
              )}

              {/* Tooltip on hover */}
              <div className="opacity-0 group-hover:opacity-100 absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 text-white text-xs rounded whitespace-nowrap pointer-events-none z-10 transition-opacity">
                {segment.label}: {(segment.value * 100).toFixed(1)}%
                <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-slate-800"></div>
              </div>
            </div>
          );
        })}
      </div>
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
    const primaryName = instructor.split(',')[0].trim().toLowerCase();
    const nameParts = primaryName.split(' ').filter(p => p.trim());
    if (nameParts.length === 0) return false;

    const lastName = nameParts[nameParts.length - 1];
    const recordName = r.instructor?.toLowerCase() || '';

    if (!recordName.includes(lastName)) return false;

    if (nameParts.length > 1) {
      const firstName = nameParts[0];
      return recordName.includes(firstName);
    }

    return true;
  }) || [];

  // Group records by semester
  const semesterGroups = instructorRecords.reduce((groups, r) => {
    const key = r.academic_period;
    if (!groups[key]) {
      groups[key] = {
        period: key,
        description: r.academic_period_desc || key,
        records: []
      };
    }
    groups[key].records.push(r);
    return groups;
  }, {});

  // Sort by academic_period descending (newest first)
  const sortedSemesters = Object.values(semesterGroups).sort((a, b) => b.period.localeCompare(a.period));

  return (
    <div className="mt-4 border-t border-line">
      <button
        onClick={handleToggle}
        className="flex min-h-11 w-full items-center justify-between py-2 text-xs font-medium text-muted transition-colors hover:text-ink"
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
            <div className="space-y-2">
              {/* Instructor-specific data - shown first if available */}
              {sortedSemesters.length > 0 ? (
                sortedSemesters.map((semesterGroup) => {
                  const records = semesterGroup.records;
                  const calculateAvg = (key) =>
                    records.reduce((sum, r) => sum + (r[key] || 0), 0) / records.length;

                  // Calculate Average GPA based on the average distribution
                  let totalGpaPoints = 0;
                  let totalGradedWeight = 0;

                  // Use a local map for GPA points if not defined globally, or defining it here
                  const GPA_POINTS = {
                    'grade_a_plus': 4.0, 'grade_a': 4.0, 'grade_a_minus': 3.7,
                    'grade_b_plus': 3.3, 'grade_b': 3.0, 'grade_b_minus': 2.7,
                    'grade_c_plus': 2.3, 'grade_c': 2.0, 'grade_c_minus': 1.7,
                    'grade_d_plus': 1.3, 'grade_d': 1.0, 'grade_d_minus': 0.7,
                    'grade_f': 0.0, 'grade_e': 0.0
                  };

                  Object.entries(GPA_POINTS).forEach(([key, points]) => {
                    const avg = calculateAvg(key);
                    totalGpaPoints += avg * points;
                    totalGradedWeight += avg;
                  });

                  const averageGpa = totalGradedWeight > 0
                    ? (totalGpaPoints / totalGradedWeight).toFixed(2)
                    : null;

                  const data = [
                    { label: 'A+', value: calculateAvg('grade_a_plus'), color: 'bg-emerald-600' },
                    { label: 'A', value: calculateAvg('grade_a'), color: 'bg-emerald-500' },
                    { label: 'A-', value: calculateAvg('grade_a_minus'), color: 'bg-emerald-400' },
                    { label: 'B+', value: calculateAvg('grade_b_plus'), color: 'bg-lime-500' },
                    { label: 'B', value: calculateAvg('grade_b'), color: 'bg-lime-400' },
                    { label: 'B-', value: calculateAvg('grade_b_minus'), color: 'bg-lime-300' },
                    { label: 'C+', value: calculateAvg('grade_c_plus'), color: 'bg-yellow-500' },
                    { label: 'C', value: calculateAvg('grade_c'), color: 'bg-yellow-400' },
                    { label: 'C-', value: calculateAvg('grade_c_minus'), color: 'bg-yellow-300' },
                    { label: 'D+', value: calculateAvg('grade_d_plus'), color: 'bg-orange-500' },
                    { label: 'D', value: calculateAvg('grade_d'), color: 'bg-orange-400' },
                    { label: 'D-', value: calculateAvg('grade_d_minus'), color: 'bg-orange-300' },
                    { label: 'F', value: calculateAvg('grade_f') + calculateAvg('grade_e'), color: 'bg-red-500' },
                    { label: 'W', value: calculateAvg('grade_w'), color: 'bg-slate-400' },
                  ];

                  return (
                    <div key={semesterGroup.period}>
                      <div className="flex items-baseline justify-between mb-0.5">
                        <h4 className="text-xs font-semibold text-slate-700">
                          {semesterGroup.description}
                          {averageGpa && (
                            <span className="ml-2 font-normal text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                              GPA: {averageGpa}
                            </span>
                          )}
                        </h4>
                        <span className="text-[10px] text-slate-500">
                          {records.length} {records.length === 1 ? 'section' : 'sections'}
                        </span>
                      </div>
                      <StackedGradeBar data={data} />
                    </div>
                  );
                })
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
    if (isUntracked) return { dot: 'bg-purdue-gold', text: 'text-muted', label: 'Availability not checked' };
    if (course.seats_remaining > 5) return { dot: 'bg-available', text: 'text-available', label: `${course.seats_remaining} seats available` };
    if (course.seats_remaining > 0) return { dot: 'bg-limited', text: 'text-limited', label: `${course.seats_remaining} ${course.seats_remaining === 1 ? 'seat' : 'seats'} left` };
    return { dot: 'bg-muted', text: 'text-muted', label: 'Full' };
  };

  const status = getStatusStyles();

  return (
    <article className="surface flex h-full flex-col p-4 transition-colors hover:border-slate-400 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
        <span className={`flex items-center gap-2 text-xs font-medium ${status.text}`}><span className={`status-dot ${status.dot}`} />{status.label}</span>
        {!isUntracked && <span className="font-mono text-[11px] text-muted">{Math.max(0, course.seats_remaining)} / {course.seats_capacity} seats</span>}
      </div>

      <div className="flex flex-1 flex-col pt-4">
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-display text-xl font-medium text-ink">{course.course_code}</h3>
            {course.schedule_type && (
              <span className="rounded border border-line bg-paper px-2 py-0.5 text-[11px] font-medium text-muted">
                {course.schedule_type}
              </span>
            )}
          </div>
          <p className="line-clamp-2 text-sm leading-5 text-muted">{course.title}</p>
        </div>

        <dl className="mb-4 space-y-2 text-xs">
          <div className="flex">
            <dt className="w-20 text-muted">Term</dt>
            <dd className="text-ink">{course.term_name || course.term_code}</dd>
          </div>
          <div className="flex">
            <dt className="w-20 text-muted">CRN</dt>
            <dd className="font-mono text-ink">{course.crn}</dd>
          </div>
          {course.section && (
            <div className="flex">
              <dt className="w-20 text-muted">Section</dt>
              <dd className="font-mono text-ink">{course.section}</dd>
            </div>
          )}
          <div className="flex">
            <dt className="w-20 text-muted">Time</dt>
            <dd className="text-ink">{course.time || 'TBA'} {course.days && `(${course.days})`}</dd>
          </div>
          <div className="flex">
            <dt className="w-20 text-muted">Instructor</dt>
            <dd className="truncate text-ink">{course.instructor || 'TBA'}</dd>
          </div>
        </dl>

        {/* Grade Distribution Section - Only show for Lecture sections */}
        {course.schedule_type === 'Lecture' && (
          <GradeSection courseCode={course.course_code} instructor={course.instructor} />
        )}

        <button
          onClick={() => onTrack(course)}
          disabled={isTracking || isTracked}
          className={`mt-auto min-h-11 w-full rounded-lg border px-4 py-2.5 text-sm font-semibold transition-colors ${isTracked
            ? 'cursor-not-allowed border-purdue-gold bg-paper text-deep-gold'
            : isTracking
              ? 'cursor-wait border-line bg-paper text-muted'
              : 'border-ink bg-canvas text-ink hover:bg-paper'
            }`}
        >
          {isTracking ? 'Adding…' : isTracked ? 'Watching' : 'Watch this section'}
        </button>
      </div>
    </article>
  );
};

export default CourseCard;
