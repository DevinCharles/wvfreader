# wvf_reader
Yokogowa Oscilloscope WVF file reader with basic plotting function

# Example Usage
```
import wvf_reader

# Get Some Data
datafiles = wvf_reader.datafile()

# Get some info on the first file
datafiles[0].info()

# Files and Traces can be accessed by name
files = datafiles[['file1','file2']]
traces = datafiles['file1'].traces['trace1,trace2']

# Plot the first and second trace, between time 0s and 5s
[datafiles[0].traces[num].plot(t_ind=(0,5)) for num in [0,1]]

# If Bokeh is installed, you can save plots to interactive HTML files
# This will down sample your data if it has more than 15,000 points
datafiles[0].traces[0].plot(output='html')

```