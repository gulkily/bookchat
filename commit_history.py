import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Get git log data
git_log_cmd = ['git', 'log', '--format=%ai']
process = subprocess.Popen(git_log_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
output, error = process.communicate()

# Process the dates
commit_dates = defaultdict(int)
dates = output.decode().strip().split('\n')

for date_str in dates:
    if date_str:
        # Convert to datetime and get just the date part
        commit_date = datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
        commit_dates[commit_date] += 1

# Sort dates and prepare data for plotting
sorted_dates = sorted(commit_dates.keys())
if sorted_dates:
    # Create lists for x and y axes
    dates_list = []
    commits_list = []
    
    # Fill in missing dates with zero commits
    current_date = sorted_dates[0]
    end_date = datetime.now().date()  # Current date
    
    while current_date <= end_date:
        dates_list.append(current_date)
        commits_list.append(commit_dates[current_date])
        current_date += timedelta(days=1)

    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.bar(dates_list, commits_list, color='#2ecc71')
    plt.title('Daily Git Commits')
    plt.xlabel('Date')
    plt.ylabel('Number of Commits')
    
    # Rotate date labels for better readability
    plt.xticks(rotation=45)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('commit_history.png')
    print("Chart has been saved as 'commit_history.png'")
else:
    print("No commit history found in this repository.")
