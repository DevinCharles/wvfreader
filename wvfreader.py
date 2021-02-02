## Imports
# Tkinter for File Dialog
from tkinter import messagebox,Tk
from tkinter.messagebox import showwarning
from tkinter.filedialog import askopenfilenames
from pathlib import Path
# For DataFile Class
import re
import numpy as np
from os.path import splitext
from os.path import split as pathsplit
from os.path import join as pathjoin
from os.path import expanduser
from struct import unpack
from collections import OrderedDict
import atexit

## Functions

# Conversion from WDF to WVF
def wdf2wvf(string,exe_loc=''):
    # Download converter from and place in your home directory:
    #   https://y-link.yokogawa.com/YL008/?V_ope_type=Show&Download_id=DL00002358&Language_id=EN
    # You may also pass a custom location WDF2WVF location in exe_loc
    import os
    from sys import exc_info
    if (exe_loc == ''):
        exe_loc = expanduser('~')+'/WDF2WVF/EXE/WDFCon.exe'
        
    if not os.path.exists(exe_loc):
        print('You are missing WDF2WVF (https://y-link.yokogawa.com/YL008/?V_ope_type=Show&Download_id=DL00002358&Language_id=EN), please install it to your home path as %HOMEPATH%/WDF2WVF/EXE/WDFCon.exe')
        raise FileExistsError(exe_loc)
        
    if os.path.isdir(string):
        for filename in os.listdir(string):
            os.system(exe_loc + ' "' + os.path.join(string,filename)+'"')
    elif os.path.exists(string):
        os.system(exe_loc + ' "' + string + '"')
    else:
        raise FileExistsError('No such file or folder ' + string)

# Handles closing open HDF5 Files on exit
open_files = []

def close_hdf5_files():
    if len(open_files) >= 1:
        for f in open_files:
            try:
                f_name = str(f)
                f.close()
                print('Closed ',f_name)
            except:
                print('Could not close ',f_name)

atexit.register(close_hdf5_files)

# Attempt to decode strings...?
def attempt_decode(value):
    try:
        return [x.decode('utf-8') for x in value]
    except:
        try:
            return value.decode('utf-8')
        except:
            return value

# Tkinter Window Setup
def tkWindow(callback,calls=''):
    root = Tk()
    root.iconify()
    try:
        output = callback(**calls)
    except:
        try:
            output = callback(*calls)
        except:
            output = callback(calls)
    finally:
        root.destroy()
    if output == 'ok':
        return
    return output

# String Type Conversion
def check_type(string_list):
    try:
        return list(map(int,string_list))
    except ValueError:
        try:
            return list(map(float,string_list))
        except ValueError:
            return string_list

# Data file constructor function
def datafile(filenames=None):
    if filenames is None:
        options = {
        'defaultextension':'.WVF',
        'filetypes' : [('Yokogowa Data File', ('*.WDF','*.WVF')),('Hierarchical Data Format (HDF5)', '.hdf5')],
        'initialdir' : str(Path.home()),
        'title' : 'Pick WVF or HDF5 files to load'
        }
        filenames = tkWindow(askopenfilenames,options)
    
    if isinstance(filenames,str):
        filenames = [filenames]
    
    if any([(splitext(filename)[1].lower() == 'wvf') | (splitext(filename)[1].lower() == 'wdf') for filename in filenames]):
        [wdf2wvf(filename) for filename in filenames if splitext(filename)[1].lower() == 'wdf']
        return IndexableDict({pathsplit(filename)[1].split('.')[0]:DataFile(filename) for filename in filenames})
    if ('hdf' in splitext(filenames[0]).lower) | ('h5' in splitext(filenames[0]).lower) :
        return read_hdf5(filenames)

# Read from generated HDF5 File
def read_hdf5(filenames):
    import h5py
    
    data_files = {}
    f = []
    
    for filename in filenames:
        try:    
            f = h5py.File(filename, 'r')
            
            # One HDF5 File can contain multiple datafiles
            for name in f.keys():
                # Create a Blank DataFile
                data_file = DataFile(None) 
                
                # Reconstruct Datafile attributes
                file_data = {k:attempt_decode(v) for k,v in f[name].attrs.items()}
                # Reconstruct Traces
                #traces = {key:Trace(value.attrs,data_file) for key,value in f[name].items()}
                traces = {key:Trace({k:attempt_decode(v) for k,v in value.attrs.items()},data_file) for key,value in f[name].items()}
                # Reorder and create indexabledict of traces
                file_data['traces'] = IndexableDict(OrderedDict(sorted(traces.items(), key=lambda item: item[1].attrs['index'])))

                for key,trace in  file_data['traces'].items():
                    block_size = trace.attrs['block_size']
                    x_gain = trace.attrs['x_gain']
                    x_offset = trace.attrs['x_offset']
                    number_of_blocks = file_data['number_of_blocks']
                    
                    # Reconstruct t data
                    t = np.tile(np.arange(0,block_size)*x_gain + x_offset,(number_of_blocks,1)).T
                    # Set Y Data
                    [setattr(trace,'y',f[name][key]) for key,trace in  file_data['traces'].items()];
                    # Set t data
                    [setattr(trace,'t',t) for key,trace in  file_data['traces'].items()];
                
                # Fill the blank DataFile
                [setattr(data_file, k, v) for k, v in file_data.items()]
                data_file.filename = filename
                data_files[name] = data_file
        finally:
            open_files.append(f)
            #f.close()
            
    return IndexableDict(data_files)
    
# ND Structured Array Creator
def dict2array(dictionary):
    array = np.array(
        [tuple(ary) for ary in np.vstack([np.array(v) for v in dictionary.values()]).T],
        dtype = [(k,'<U'+str(len(v[np.argmax([len(arg) for arg in v])]))) if isinstance(v[0],str) else (k,type(v[np.argmax(v)]))  for k,v in dictionary.items()],
    )
    return array

## Classes
# Self Initializing Dictionary Class
class Dict(dict):
    def __missing__(self, key):
        self[key] = Dict()
        return self[key]

# Indexable Dictionary
class IndexableDict(OrderedDict):
    def __getitem__(self,key):
        if isinstance(key,int) | isinstance(key,slice):
            return list(self.values())[key]
        if isinstance(key,list):
            keys = key
            out = []
            for key in keys:
                if isinstance(key,str):
                    try:
                        out.append([v for k,v in self.items() if k.lower().replace(' ','_')==key.lower().replace(' ','_')][0])
                    except IndexError:
                        raise Exception('Key '+key+' does not exist.\nAvailable Keys:\n'+'\n'.join([k for k in self.keys()]))
            return out
        elif isinstance(key,str):
            try:
                return [v for k,v in self.items() if k.lower().replace(' ','_')==key.lower().replace(' ','_')][0]
            except IndexError:
                raise Exception('Key '+key+' does not exist.\nAvailable Keys:\n'+'\n'.join([k for k in self.keys()]))
        else:
            raise

class DataFile():
    ##TODO: Add plot method to plot multiple traces
    def __init__(self, filename=None, verbose=False):
        if filename==None:
            return
        else:
            self.filename = filename
            file_info, trace_info_array = self.read_hdr()
            [setattr(self, k, v) for k, v in file_info.items()]
            
            self.traces =  IndexableDict({})
            
            for info in trace_info_array:
                self.traces[info['name']] = Trace({key:value for key,value in zip(info.dtype.names,info)},self)
            
            self.date = file_info['date']
            self.name = pathsplit(filename)[1].split('.')[0]
    
    def read_hdr(self):
        # Make sure we're looking at the HDR file
        filename = splitext(self.filename)[0] + '.HDR'
        data = Dict()
        main_key = None
        
        #try:
        #    f = open(filename,'r')
        #    f.close()
        #except FileNotFoundError:
        #    filename = self.filename.split('.')[0] + '.hdr'

        with open(filename,'r') as content:
            # Walk the file one line at a time
            for line in content:
                
                # Check to see if it's a section
                section_match = re.match(r'(\${1})(.*)',line)
                if section_match:
                    main_key = section_match.group(2).strip()
                        
                # This is Not a Section Heading, Get the Data
                else:
                    # Make sure we're in a section
                    if main_key is not None:
                        # Split a line of data into columns, removing line return
                        column = line.strip().split()
                        if len(column)>1:
                            # Create dictionary as data[Section][Type] = dataArray
                            key = column.pop(0)
                            data[main_key][key] = check_type(column)
                            if len(data[main_key][key])==1:
                                data[main_key][key] = data[main_key][key][0]
        
            
        data['filename'] = filename
        file_info,trace_info_array = self.parse_header(data)
        return file_info,trace_info_array
    
    def parse_header(self,data):
        ## Per Trace Data
        translator = {
            'block_size':'BlockSize',
            'date':'Date',

            'x_offset':'HOffset',
            'x_gain':'HResolution',
            'x_unit':'HUnit',

            'y_offset':'VOffset',
            'y_gain':'VResolution',
            'y_unit':'VUnit',

            'name':'TraceName',
            'data_type':'VDataType',
        }

        file_data = {key:[] for key in translator.keys()}

        for group in [key for key in data.keys() if 'group' in key.lower()]:
            for k,v in translator.items():
                if isinstance(data[group][v],list):
                    file_data[k].extend(data[group][v])
                else:
                    file_data[k].append(data[group][v])
        
        ## Per File Data
        file_data['filename'] = data['filename']

        if data['PublicInfo']['Endian'] == 'Big':
            endian = '>'
        elif (data['PublicInfo']['Endian'] == 'Little')|(data['PublicInfo']['Endian'] == 'Ltl'):
            endian = '<'
        file_data['real_capture_time'] = [data['Group1'][key][0] for key in data[group].keys() if 'time' in key.lower()]
        file_data['data_offset'] = data['PublicInfo']['DataOffset']
        file_data['number_of_blocks'] = data['Group1']['BlockNumber']
        file_data['index'] = [num for num in range(0,len(file_data['name']))]
        
        ## Parse Collected Data
        file_data['num_bytes'] = [int(dt[2]) for dt in file_data['data_type']]
        file_data['date'] = file_data['date'][0]
        
        fmt_str = []
        for num,fmt in enumerate(file_data['data_type']):        
            letter = {'I':{'2':'h','4':'i','8':'q'},'F':{'4':'f','8':'d'}}[fmt[0]][fmt[2]]
            if fmt[0:2] == 'IU':
                letter = letter.upper()
            elif fmt[0:2] == 'FU':
                print('WARING: CONVERTING UNSIGNED FLOAT TO FLOAT MAY PRODUCE ERRORS')
            fmt_str.append(endian + str(file_data['block_size'][num])+letter)
        file_data['fmt_str'] = fmt_str
        
        trace_info_array = dict2array({key:value for key,value in file_data.items() if isinstance(file_data[key],list) and len(file_data[key])==len(file_data['name'])})
        file_info ={key:value for key,value in file_data.items() if key not in trace_info_array.dtype.names}
        
        return file_info,trace_info_array
        
    def write_hdf5(self,filename=None, compression='gzip'):
        import h5py
        if filename is None:
            from tkinter.filedialog import asksaveasfilename
            options = {
                'defaultextension':'.hdf5',
                'filetypes' : [('Hierarchical Data Format (HDF5)', '.hdf5')],
                'initialdir' : str(Path.home()),
                'initialfile' : self.name,
                'title' : 'Save As HDF5 File'
            }
            filename = tkWindow(asksaveasfilename,options)
            
        try:
            f = h5py.File(filename, 'a')

            file_group = f.create_group(self.name)
            #trace_group = file_group.create_group('traces')
            
            # Write File Attributes
            for attr_name, attr_value in self.__dict__.items():
                if attr_name != 'traces':
                    if isinstance(attr_value,np.str_) | isinstance(attr_value,str):
                        # Handles conversion from Unicode... not sure that I'm doing this right?
                        file_group.attrs[attr_name] = attr_value.encode('utf-8')#np.string_(attr_value)
                    elif isinstance(attr_value,list):
                        if (isinstance(attr_value[0],np.str_) | isinstance(attr_value[0],str)):
                            file_group.attrs[attr_name] = [x.encode('utf-8') for x in attr_value] #np.string_(x)
                        else:
                            file_group.attrs[attr_name] = attr_value
                    else:
                        file_group.attrs[attr_name] = attr_value
                    
            # Write Trace Data and Attributes
            for name,trace in self.traces.items():
                dataset = file_group.create_dataset(name, data=trace.y, compression=compression)
                
                for attr_name, attr_value in trace.attrs.items():
                    if isinstance(attr_value,np.str_) | isinstance(attr_value,str):
                        # Handles conversion from Unicode... not sure that I'm doing this right?
                        dataset.attrs[attr_name] = np.string_(attr_value)
                    elif isinstance(attr_value,list):
                        if (isinstance(attr_value[0],np.str_) | isinstance(attr_value[0],str)):
                            dataset.attrs[attr_name] = [np.string_(x) for x in attr_value]
                        else:
                            dataset.attrs[attr_name] = attr_value
                    else:
                        dataset.attrs[attr_name] = attr_value
            f.close()
        #except ValueError:
        #    pass
        except:
            print(self.name + ' failed to write to HDF5 File '+filename)
        finally:
            f.close()
    
    def info(self):
        # Trace Table Info Setup
        fmts = ['|{:^9}','|{:^19}','|{:^9}','|{:^15}|']
        header = ''.join([fmt.format(value) for fmt,value in zip(fmts,['INDEX','TRACE','UNITS','SAMPLE TIME'])])
        t_data = [[trace.attrs['index'],trace.attrs['name'],trace.attrs['y_unit'],str(trace.attrs['x_gain'])+' '+trace.attrs['x_unit']] for trace in self.traces.values()]
        
        filename = self.filename
        x = int((len(header)-15-3)/2)
        
        if len(filename) > len(header)-15:
            filename = filename[:x]+'...'+filename[-x:]
        
        print('')
        print('\t'+'#'*len(header))
        print('')
        print('\tFile Name  :   ',self.name)
        print('\tFile Date  :   ',self.date)
        print('\tNo. Blocks :   ',self.number_of_blocks)
        print('\tFile Path  :   ',filename)
        print('\t')#TABLE BELOW#
        print('\t'+'-'*len(header))
        print('\t'+header)
        print('\t'+'='*len(header))
        [print('\t'+''.join([fmt.format(value) for fmt,value in zip(fmts,values)])) for values in t_data]
        print('\t'+'-'*len(header))
        
class Trace():
    def __init__(self,trace_info,parent):
        self.attrs = trace_info
        self.parent = parent
        
    def __getattr__(self,name):
        if name in ('t','y'):
            self.t, self.y = self.get_data()
            if name == 't':
                return self.t
            else:
                return self.y
        else:
            print(name + ' does not exist')
            return None
    
    def get_data(self):  
        ## Read from WVF File
        number_of_blocks = self.parent.number_of_blocks
        data_offset = self.parent.data_offset
        trace_info = self.attrs
        
        trace_number = trace_info['index']
        block_size = trace_info['block_size']
        num_bytes = trace_info['num_bytes']
        fmt_str = trace_info['fmt_str']
        
        x_gain = trace_info['x_gain']
        x_offset = trace_info['x_offset']
        y_gain = trace_info['y_gain']
        y_offset = trace_info['y_offset']
        
        with open(splitext(self.parent.filename)[0]+'.WVF','rb') as file:
            y = np.empty((block_size,number_of_blocks))
            for block_number in range(0,number_of_blocks):
                file.seek((trace_number*number_of_blocks + block_number)*(num_bytes*block_size) + data_offset)
                buffer = file.read(num_bytes*block_size)
                y[:,block_number] = unpack(fmt_str,buffer)
                y[:,block_number] = y[:,block_number]*y_gain + y_offset
            t = np.tile(np.arange(0,block_size)*x_gain + x_offset,(number_of_blocks,1)).T
        
        return t,y
    
    def plot(self,block=None,output='screen',t_ind=None):
        ### SETUP ###
        if block is None:
            t = self.t
            y = self.y
            if self.parent.number_of_blocks >= 2:
                legend = ['Block '+ str(num) for num in range(0,self.parent.number_of_blocks)]
            else:
                legend = ['/'+self.parent.name+'/'+self.attrs['name']]
        else:
            t = self.t[:,block]
            y = self.y[:,block]
            if isinstance(block,int):
                legend = ['Block '+ str(block)]
            else:
                legend = ['Block '+ str(num) for num in block]
        
        if t_ind != None:
            y = y[(t>=t_ind[0])&(t<=t_ind[1])]
            t = t[(t>=t_ind[0])&(t<=t_ind[1])]
            
                
        title = '/'+self.parent.name+'/'+self.attrs['name']
        x_label = 'Time [' + self.attrs['x_unit'] + ']'
        y_label = self.attrs['name']+ ' [' + self.attrs['y_unit'] + ']'
        out_filename = pathjoin(pathsplit(self.parent.filename)[0],self.parent.name+'-'+self.attrs['name'])
        
        ### BOKEH ###
        if any(str in output for str in ['bokeh','html']):
            from bokeh.plotting import figure
            from bokeh.io import show, save
            from bokeh.resources import Resources
            from bokeh.models.glyphs import Text
            from scipy.signal import resample
            
            t = t[:,0]
            y = y[:,0]
            
            resample_size = int(15e3)
            if len(t) > resample_size:
                t = np.linspace(t[0],t[-1],resample_size)
                y = resample(y,resample_size)
                title = title + '\tResampled at ~'+str(int(round(1/np.mean(np.diff(t)))))+'Hz'
            
            plot = figure(
                width=1024,
                height=768,
                tools='hover,pan,wheel_zoom,xwheel_zoom,ywheel_zoom,undo,reset,save',
                active_drag='pan',
                active_scroll='xwheel_zoom',
                title=title,
                x_axis_label=x_label,
                y_axis_label=y_label,
                #x_range=[],
                #y_range=[]
                )
                
            plot.line(t,y,legend=legend)
            
            if 'html' in output:
                save(plot, filename=out_filename+'.html', resources=Resources('inline'), title=title)
            else:
                show(plot)
                
        ### MATPLOTLIB ###
        else:
            from matplotlib import pyplot as plt
            try:
                cur_leg = [leg._text for leg in plt.gca().legend_.texts]
            except AttributeError:
                cur_leg = []
            
            cur_leg.extend(legend)
            
            plt.plot(t,y)
            plt.legend(cur_leg)
            plt.title(title)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            
            ax = plt.gca()
            ax.set_axisbelow(True)
            ax.minorticks_on()
            ax.grid(which='major', linestyle='-', linewidth='1', color='black')
            ax.grid(which='minor', linestyle=':', linewidth='0.5', color='gray')
            
            if output == 'screen':
                plt.show(block=('blocking' in output))
            elif output == 'pdf':
                from matplotlib.backends.backend_pdf import PdfPages
                pdf_file = out_filename+'.pdf'
                pp = PdfPages(pdf_file)
                pp.savefig()
                pp.close()
        
