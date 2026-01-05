import { useState, useEffect } from 'react';
import { coursesAPI, tracksAPI } from '../services/api';
import CourseCard from '../components/CourseCard';
import { trackEvent, EVENTS } from '../hooks/usePostHog';

const Search = () => {
  const [query, setQuery] = useState('');
  const [courses, setCourses] = useState([]);
  const [trackedCRNs, setTrackedCRNs] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    loadTrackedCourses();
  }, []);

  const loadTrackedCourses = async () => {
    try {
      const response = await tracksAPI.getAll();
      const crns = new Set(response.data.map(t => t.course.crn));
      setTrackedCRNs(crns);
    } catch (err) {
      console.error('Failed to load tracked courses:', err);
      trackEvent(EVENTS.API_ERROR, { action: 'load_tracked_courses', error: err.message });
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    trackEvent(EVENTS.SEARCH_PERFORMED, { query: query.trim() });

    try {
      setLoading(true);
      setError('');
      setSearched(true);
      const response = await coursesAPI.search(query);
      setCourses(response.data);

      if (response.data.length === 0) {
        setError('No courses found');
        trackEvent(EVENTS.SEARCH_NO_RESULTS, { query: query.trim() });
      } else {
        trackEvent(EVENTS.SEARCH_RESULTS_SHOWN, {
          query: query.trim(),
          results_count: response.data.length,
          available_count: response.data.filter(c => c.seats_remaining > 0).length,
        });
      }
    } catch (err) {
      setError('Failed to search courses');
      trackEvent(EVENTS.API_ERROR, { action: 'search_courses', query: query.trim(), error: err.message });
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleTrack = async (crn) => {
    const course = courses.find(c => c.crn === crn);
    trackEvent(EVENTS.COURSE_TRACK_CLICKED, {
      crn,
      course_code: course?.course_code,
      seats_remaining: course?.seats_remaining,
      seats_capacity: course?.seats_capacity,
    });

    try {
      setTracking(crn);
      await tracksAPI.create({ crn, notify_on_open: true, notify_on_close: false });
      setTrackedCRNs(new Set([...trackedCRNs, crn]));
      trackEvent(EVENTS.COURSE_TRACKED, {
        crn,
        course_code: course?.course_code,
        seats_remaining: course?.seats_remaining,
      });
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to track course');
      trackEvent(EVENTS.COURSE_TRACK_FAILED, {
        crn,
        course_code: course?.course_code,
        error: err.response?.data?.detail || err.message,
      });
      console.error(err);
    } finally {
      setTracking(null);
    }
  };


  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-800">Search Courses</h1>
          <p className="text-slate-500 text-sm sm:text-base mt-1">Find courses by subject, code, or CRN</p>
        </div>

        {/* Search */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-6 mb-6">
          <form onSubmit={handleSearch}>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search courses..."
                  className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent text-base"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="bg-slate-800 text-white px-6 py-3 rounded-lg font-medium hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>

          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg mb-6 text-sm">
            {error}. Try searching by subject code (CS, MA), course number (CS 18000), or CRN.
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin"></div>
          </div>
        )}

        {/* Results */}
        {!loading && courses.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-800">
                {courses.length} {courses.length === 1 ? 'result' : 'results'}
              </h2>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {courses.map(course => (
                <CourseCard
                  key={course.id}
                  course={course}
                  onTrack={handleTrack}
                  isTracking={tracking === course.crn}
                  isTracked={trackedCRNs.has(course.crn)}
                />
              ))}
            </div>
          </>
        )}

        {/* Initial state */}
        {!loading && !searched && (
          <div className="bg-white rounded-xl border border-slate-200 p-8 sm:p-12 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-slate-800 mb-2">Search for courses</h2>
            <p className="text-slate-500 text-sm max-w-sm mx-auto">
              Enter a subject code, course number, or CRN to find courses
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Search;
