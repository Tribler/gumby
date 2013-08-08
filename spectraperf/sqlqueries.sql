

# Select proportion of difference in range to max value of range
# (i.e., how large is the range compared to the max value).
# Take the average for ranges for a stacktrace_id in a revision.
SELECT revision, stacktrace_id, AVG((max_value*1.0-min_value)/max_value) FROM range 
JOIN profile ON profile.id = profile_id 
GROUP BY revision, stacktrace_id
ORDER BY stacktrace_id
