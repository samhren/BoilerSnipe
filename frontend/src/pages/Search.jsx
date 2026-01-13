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

const SORT_OPTIONS = [
  { label: 'Course Code (Asc)', value: 'code_asc' },
  { label: 'Course Code (Desc)', value: 'code_desc' },
  { label: 'Seats (High to Low)', value: 'seats_desc' },
  { label: 'Seats (Low to High)', value: 'seats_asc' },
];

const Search = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const [query, setQuery] = useState(initialQuery);
  const [courses, setCourses] = useState([]);
  const [trackedCRNs, setTrackedCRNs] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  // Filter & Sort States
  const [showFilters, setShowFilters] = useState(false);
  const [selectedDays, setSelectedDays] = useState(new Set());
  const [selectedTypes, setSelectedTypes] = useState(new Set());
  const [sortOption, setSortOption] = useState(SORT_OPTIONS[0].value);

  useEffect(() => {
    loadTrackedCourses();
  }, []);

  // Keep the URL's query param (?q=) in sync with the current input value
  useEffect(() => {
    const current = searchParams.get('q') || '';
    if (query !== current) {
      const params = new URLSearchParams(searchParams);
      if (query && query.trim()) {
        params.set('q', query);
      } else {
        params.delete('q');
      }
      setSearchParams(params, { replace: true });
    }
  }, [query]);

  // Reset filters when a new search is performed
  useEffect(() => {
    if (searched) {
      // Optional: Decisions to keep or reset filters can be made here. 
      // Currently keeping them as user might refine search query but want same filters.
    }
  }, [courses]);

  const loadTrackedCourses = async () => {
    try {
      const response = await tracksAPI.getAll();
      const crns = new Set(response.data.map(t => t.course.crn));
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

  const handleTrack = async (crn) => {
    try {
      setTracking(crn);
      await tracksAPI.create({ crn, notify_on_open: true, notify_on_close: false });
      setTrackedCRNs(new Set([...trackedCRNs, crn]));
      console.log('Tracked Course:', { crn });
      rybbit.track('Track Course', { crn });
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to track course');
      console.error(err);
    } finally {
      setTracking(null);
    }
  };

  // --- Filtering & Sorting Logic ---

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

    // 3. Sort
    result.sort((a, b) => {
      switch (sortOption) {
        case 'code_asc':
          return a.course_code.localeCompare(b.course_code);
        case 'code_desc':
          return b.course_code.localeCompare(a.course_code);
        case 'seats_desc':
          return (b.seats_remaining || 0) - (a.seats_remaining || 0);
        case 'seats_asc':
          return (a.seats_remaining || 0) - (b.seats_remaining || 0);
        default:
          return 0;
      }
    });

    return result;
  }, [courses, selectedDays, selectedTypes, sortOption]);

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

        {/* Filters & Results Info */}
        {!loading && searched && (
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold text-slate-800">
                  {filteredCourses.length} {filteredCourses.length === 1 ? 'result' : 'results'}
                  {courses.length !== filteredCourses.length && (
                    <span className="text-slate-500 font-normal text-sm ml-2">
                      (filtered from {courses.length})
                    </span>
                  )}
                </h2>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="text-sm text-slate-600 hover:text-slate-800 flex items-center gap-1 font-medium bg-white px-3 py-1.5 rounded-lg border border-slate-200 hover:border-slate-300 transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  {showFilters ? 'Hide Filters' : 'Show Filters'}
                  {(selectedDays.size > 0 || selectedTypes.size > 0) && (
                    <span className="bg-slate-800 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                      {selectedDays.size + selectedTypes.size}
                    </span>
                  )}
                </button>
              </div>

              {/* Sort Control */}
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <span className="text-sm text-slate-500 whitespace-nowrap">Sort by:</span>
                <select
                  value={sortOption}
                  onChange={(e) => setSortOption(e.target.value)}
                  className="text-sm border-gray-200 rounded-md py-1.5 pl-3 pr-8 w-full sm:w-auto focus:ring-slate-500 focus:border-slate-500"
                >
                  {SORT_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Expandable Filter Panel */}
            {showFilters && (
              <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-6 mb-6 animate-in slide-in-from-top-2 duration-200">
                <div className="grid sm:grid-cols-2 gap-6">
                  {/* Day Filter */}
                  <div>
                    <h3 className="text-sm font-semibold text-slate-700 mb-3">Day of Week</h3>
                    <div className="flex flex-wrap gap-2">
                      {DAYS_MAP.map(day => {
                        const isSelected = selectedDays.has(day.value);
                        return (
                          <button
                            key={day.value}
                            onClick={() => toggleDay(day.value)}
                            className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${isSelected
                                ? 'bg-slate-800 text-white border-slate-800'
                                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
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
                    <h3 className="text-sm font-semibold text-slate-700 mb-3">Class Type</h3>
                    {availableTypes.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {availableTypes.map(type => {
                          const isSelected = selectedTypes.has(type);
                          return (
                            <button
                              key={type}
                              onClick={() => toggleType(type)}
                              className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${isSelected
                                  ? 'bg-slate-800 text-white border-slate-800'
                                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
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
                  <div className="mt-4 pt-4 border-t border-slate-100 flex justify-end">
                    <button
                      onClick={() => {
                        setSelectedDays(new Set());
                        setSelectedTypes(new Set());
                      }}
                      className="text-sm text-red-600 hover:text-red-700 font-medium"
                    >
                      Clear All Filters
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

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
        {!loading && filteredCourses.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredCourses.map(course => (
              <CourseCard
                key={course.id}
                course={course}
                onTrack={handleTrack}
                isTracking={tracking === course.crn}
                isTracked={trackedCRNs.has(course.crn)}
              />
            ))}
          </div>
        )}

        {!loading && searched && filteredCourses.length === 0 && courses.length > 0 && (
          <div className="text-center py-12">
            <p className="text-slate-500">No courses match your active filters.</p>
            <button
              onClick={() => {
                setSelectedDays(new Set());
                setSelectedTypes(new Set());
              }}
              className="text-slate-800 font-medium mt-2 hover:underline"
            >
              Clear filters
            </button>
          </div>
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
