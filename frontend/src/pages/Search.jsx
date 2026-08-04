import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { coursesAPI, tracksAPI } from '../services/api';
import rybbit from '../services/rybbit';
import CourseCard from '../components/CourseCard';

const DAYS_MAP = [
  { label: 'Mon', value: 'M' },
  { label: 'Tue', value: 'T' },
  { label: 'Wed', value: 'W' },
  { label: 'Thu', value: 'R' },
  { label: 'Fri', value: 'F' },
  { label: 'Sat', value: 'S' },
  { label: 'Sun', value: 'U' },
];

const Search = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize state from URL params
  const initialQuery = searchParams.get('q') || '';
  const initialDays = searchParams.get('days') ? new Set(searchParams.get('days').split(',')) : new Set();
  const initialTypes = searchParams.get('types') ? new Set(searchParams.get('types').split(',')) : new Set();

  const [query, setQuery] = useState(initialQuery);
  const [courses, setCourses] = useState([]);
  const [trackedCRNs, setTrackedCRNs] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  // Filter States
  const [showFilters, setShowFilters] = useState(initialDays.size > 0 || initialTypes.size > 0);
  const [selectedDays, setSelectedDays] = useState(initialDays);
  const [selectedTypes, setSelectedTypes] = useState(initialTypes);

  useEffect(() => {
    loadTrackedCourses();
  }, []);

  // Update URL params when state changes
  useEffect(() => {
    const params = new URLSearchParams();

    if (query.trim()) params.set('q', query.trim());

    if (selectedDays.size > 0) {
      params.set('days', Array.from(selectedDays).join(','));
    }

    if (selectedTypes.size > 0) {
      params.set('types', Array.from(selectedTypes).join(','));
    }

    // Only update if the string representation is different to avoid unnecessary updates
    if (params.toString() !== searchParams.toString()) {
      setSearchParams(params, { replace: true });
    }
  }, [query, selectedDays, selectedTypes, setSearchParams, searchParams]);

  const loadTrackedCourses = async () => {
    try {
      const response = await tracksAPI.getAll();
      const crns = new Set(response.data.map(t => `${t.course.term_code}:${t.course.crn}`));
      setTrackedCRNs(crns);
    } catch (err) {
      console.error('Failed to load tracked courses:', err);
    }
  };

  const performSearch = async (q) => {
    if (!q.trim()) return;
    try {
      setLoading(true);
      setError('');
      setSearched(true);
      const response = await coursesAPI.search(q);
      setCourses(response.data);

      if (response.data.length === 0) {
        setError('No courses found');
      }

      rybbit.track('Course Search', {
        query: q,
        count: response.data.length,
        has_results: response.data.length > 0
      });
    } catch (err) {
      setError('Failed to search courses');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    await performSearch(query);
  };

  // If arriving with ?q= preset, run the search automatically once
  useEffect(() => {
    if (initialQuery && !searched && courses.length === 0 && !loading) {
      performSearch(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTrack = async (course) => {
    try {
      const trackKey = `${course.term_code}:${course.crn}`;
      setTracking(trackKey);
      await tracksAPI.create({
        crn: course.crn,
        term_code: course.term_code,
        notify_on_open: true,
        notify_on_close: false
      });
      setTrackedCRNs(new Set([...trackedCRNs, trackKey]));
      console.log('Tracked Course:', { crn: course.crn, term_code: course.term_code });
      rybbit.track('Track Course', { crn: course.crn, term_code: course.term_code });
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to track course');
      console.error(err);
    } finally {
      setTracking(null);
    }
  };

  // --- Filtering Logic ---

  // derived available types from the current search results
  const availableTypes = useMemo(() => {
    const types = new Set(courses.map(c => c.schedule_type).filter(Boolean));
    return Array.from(types).sort();
  }, [courses]);

  const filteredCourses = useMemo(() => {
    let result = [...courses];

    // 1. Filter by Days (Union: Show if course has ANY of the selected days)
    if (selectedDays.size > 0) {
      result = result.filter(course => {
        if (!course.days) return false;
        // Check if any char in course.days is in selectedDays
        for (let char of course.days) {
          if (selectedDays.has(char)) return true;
        }
        return false;
      });
    }

    // 2. Filter by Type (Union)
    if (selectedTypes.size > 0) {
      result = result.filter(course =>
        course.schedule_type && selectedTypes.has(course.schedule_type)
      );
    }

    return result;
  }, [courses, selectedDays, selectedTypes]);

  const toggleDay = (day) => {
    const next = new Set(selectedDays);
    if (next.has(day)) next.delete(day);
    else next.add(day);
    setSelectedDays(next);
  };

  const toggleType = (type) => {
    const next = new Set(selectedTypes);
    if (next.has(type)) next.delete(type);
    else next.add(type);
    setSelectedTypes(next);
  };

  return (
    <div className="page-shell">
      <div className="page-container">
        {/* Header */}
        <div className="mb-7 border-b border-line pb-7">
          <p className="eyebrow mb-2">Fall 2026 catalog</p>
          <h1 className="section-title">Find a section</h1>
          <p className="mt-2 text-sm text-muted">Search by subject, course number, or CRN. Each result is an individual section.</p>
        </div>

        {/* Search */}
        <div className="sticky top-16 z-30 -mx-5 mb-7 border-b border-line bg-canvas/95 px-5 py-4 backdrop-blur sm:static sm:mx-0 sm:rounded-lg sm:border sm:p-5">
          <form onSubmit={handleSearch}>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 relative">
                  <svg className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="CS 18000 or 12345"
                  className="input-field pl-10 text-base"
                  aria-label="Search courses"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="btn-primary px-7"
              >
                {loading ? 'Searching…' : 'Search'}
              </button>
            </div>
          </form>
        </div>

        {/* Filters & Results Info */}
        {!loading && searched && (
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                  <h2 className="font-display text-xl font-medium text-ink">
                  {filteredCourses.length} {filteredCourses.length === 1 ? 'result' : 'results'}
                  {courses.length !== filteredCourses.length && (
                    <span className="ml-2 font-sans text-sm font-normal text-muted">
                      (filtered from {courses.length})
                    </span>
                  )}
                </h2>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="flex min-h-10 items-center gap-1 rounded-lg border border-line bg-canvas px-3 py-1.5 text-sm font-medium text-muted transition-all hover:border-slate-400 hover:text-ink"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  {showFilters ? 'Hide Filters' : 'Show Filters'}
                  {(selectedDays.size > 0 || selectedTypes.size > 0) && (
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-ink text-xs text-canvas">
                      {selectedDays.size + selectedTypes.size}
                    </span>
                  )}
                </button>
              </div>
            </div>

            {/* Expandable Filter Panel */}
            {showFilters && (
              <div className="surface mb-6 p-4 sm:p-6">
                <div className="grid sm:grid-cols-2 gap-6">
                  {/* Day Filter */}
                  <div>
                    <h3 className="mb-3 text-sm font-semibold text-ink">Day of week</h3>
                    <div className="flex flex-wrap gap-2">
                      {DAYS_MAP.map(day => {
                        const isSelected = selectedDays.has(day.value);
                        return (
                          <button
                            key={day.value}
                            onClick={() => toggleDay(day.value)}
                            className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${isSelected
                              ? 'border-ink bg-ink text-canvas'
                              : 'border-line bg-canvas text-muted hover:border-slate-400 hover:bg-paper'
                              }`}
                          >
                            {day.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Type Filter */}
                  <div>
                    <h3 className="mb-3 text-sm font-semibold text-ink">Class type</h3>
                    {availableTypes.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {availableTypes.map(type => {
                          const isSelected = selectedTypes.has(type);
                          return (
                            <button
                              key={type}
                              onClick={() => toggleType(type)}
                              className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${isSelected
                                ? 'border-ink bg-ink text-canvas'
                                : 'border-line bg-canvas text-muted hover:border-slate-400 hover:bg-paper'
                                }`}
                            >
                              {type}
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400">No types available for current results.</p>
                    )}
                  </div>
                </div>

                {/* Clear Filters */}
                {(selectedDays.size > 0 || selectedTypes.size > 0) && (
                  <div className="mt-4 flex justify-end border-t border-line pt-4">
                    <button
                      onClick={() => {
                        setSelectedDays(new Set());
                        setSelectedTypes(new Set());
                      }}
                      className="text-sm text-red-600 hover:text-red-700 font-medium"
                    >
                      Clear all filters
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div role="status" className="mb-6 rounded-md border border-line border-l-[3px] border-l-limited bg-canvas px-4 py-3 text-sm text-limited">
            {error}. Try searching by subject code (CS, MA), course number (CS 18000), or CRN.
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-ink" aria-label="Searching" />
          </div>
        )}

        {/* Results */}
        {!loading && filteredCourses.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredCourses.map(course => (
              <CourseCard
                key={`${course.term_code}:${course.crn}`}
                course={course}
                onTrack={handleTrack}
                isTracking={tracking === `${course.term_code}:${course.crn}`}
                isTracked={trackedCRNs.has(`${course.term_code}:${course.crn}`)}
              />
            ))}
          </div>
        )}

        {!loading && searched && filteredCourses.length === 0 && courses.length > 0 && (
          <div className="surface py-12 text-center">
            <p className="font-display text-xl font-medium">No sections match those filters.</p>
            <button
              onClick={() => {
                setSelectedDays(new Set());
                setSelectedTypes(new Set());
              }}
              className="mt-3 text-sm font-semibold text-ink underline decoration-purdue-gold decoration-2 underline-offset-4"
            >
              Clear filters
            </button>
          </div>
        )}

        {/* Initial state */}
        {!loading && !searched && (
          <div className="surface px-8 py-14 text-center sm:px-12 sm:py-16">
            <p className="eyebrow mb-3">Start with what you know</p>
            <h2 className="font-display text-2xl font-medium text-ink">Search the course catalog.</h2>
            <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-muted">
              Try a subject like CS, a course like MA 26100, or the five-digit CRN.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Search;
