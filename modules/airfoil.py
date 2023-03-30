#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

    Airfoil and operations on it 

"""
import os
import numpy as np
import math
from common_utils import * 
from airfoil_line_spline import LineOfAirfoil, panel_angles


class Airfoil:
    """ 

    Airfoil object to handle a airfoil direct related things  

    """
    isStrakAirfoil  = False
    isExample       = False                      # vs. Example_Airfoil 

    def __init__(self, pathFileName = None, name = None, workingDir= None):
        """
        Main constructor for new Airfoil

        Args:
            :pathFileName: optional - string of existinng airfoil path and name \n
            :name: optional - name of airfoil - no checks performed 
        """

        self.pathFileName = None
        self.workingDir   = workingDir if workingDir is not None else ''
        self.name         = name if name is not None else ''
        self.sourceName = None                  # the long name out of the two blended airfoils (TSrakAirfoil)

        self._x       = None
        self._y       = None
        self._upper   = None                    # upper surface line object 
        self._lower   = None                    # lower surface line object 
        self._camber  = None                    # camber line object 
        self._thickness = None                  # thickness line object 


        if (pathFileName is not None): 
            if os.path.isabs (pathFileName):
                checkPath = pathFileName
            else:
                checkPath = os.path.join (self.workingDir, pathFileName)
            if not os.path.isfile(checkPath):
                ErrorMsg ("Airfoil file \'%s\' does not exist. Couldn\'t create Airfoil" % checkPath)
                self.name = "-- ? --"
            else:
                self.pathFileName = pathFileName
                self.name = os.path.splitext(os.path.basename(self.pathFileName))[0]  # load will get the real name
        elif (not name):
            self.name = "-- ? --"


    @classmethod
    def onDict(cls, dataDict, workingDir = None):
        """
        Alternate constructor for new Airfoil based on dictionary 

        Args:
            :dataDict: dictionary with "name" and "file" keys
            :workingDir: home of dictionary (paramter file) 
        """
        pathFileName  = fromDict(dataDict, "file", None)
        name          = fromDict(dataDict, "name", None)
        return cls(pathFileName = pathFileName, name = name, workingDir=workingDir)

    def _save (self, airfoilDict):
        """ stores the variables into the dataDict - returns the filled dict"""
        # will be overloaded 
        toDict (airfoilDict, "file",    self.pathFileName) 
        return airfoilDict
 

    def __repr__(self) -> str:
        # overwrite to get a nice print string 
        info = f"\'{self.name}\'"
        return f"{type(self).__name__} {info}"

    @property
    def x (self): return self._x
        
    @property
    def y (self): return self._y

    @property
    def x_rebuild (self):
        "x coordinates - rebuild from upper and lower "
        if self._upper is None: 
            return []
        else:
            return np.concatenate ((np.flip(self._upper.x), self._lower.x[1:]))
        
    @property
    def y_rebuild (self):
        "y coordinates - rebuild from upper and lower "
        if self._upper is None: 
            return []
        else:
            return np.concatenate ((np.flip(self._upper.y), self._lower.y[1:]))
        

    @property
    def isExisting (self):
        return not self.pathFileName is None
    
    @property
    def isLoaded (self):
        return self._x is not None and len(self._x) > 10
    
    @property
    def isNormalized (self):
        
        if self._x is None: return False

        xteUp, yteUp, xteLow, yteLow = self.te_fromPoints
        if xteUp != 1.0 or xteLow != 1.0: return False
        if yteUp != - yteLow: return False

        xle, yle = self.le_fromPoints 
        if xle != 0.0 or yle != 0.0: return False

        return True
    
    @property
    def le_i (self) -> int: 
        """ the index of leading edge in x coordinate array"""
        return int(np.argmin (self._x))

    @property
    def le_fromPoints (self): 
        """ returns leading edge x,y of point coordinate data """
        ile = np.argmin (self._x)
        return self._x[ile], self._y[ile]
    
    @property 
    def le_panelAngle (self): 
        """returns the upper and lower angle of the 2 panels at leading edge - should be less 90"""

        # panang1 = atan((zt(2)-zt(1))/(xt(2)-xt(1))) *                &
        #           180.d0/acos(-1.d0)
        # panang2 = atan((zb(1)-zb(2))/(xb(2)-xb(1))) *                &
        #           180.d0/acos(-1.d0)
        # maxpanang = max(panang2,panang1)
        ile = self.le_i
        angleUp = math.atan ((self.y[ile-1] - self.y[ile])/(self.x[ile-1] - self.x[ile])) * 180.0 / math.acos(-1)
        angleLo = math.atan ((self.y[ile] - self.y[ile+1])/(self.x[ile+1] - self.x[ile])) * 180.0 / math.acos(-1)

        return angleUp, angleLo 

    @property
    def te_fromPoints (self): 
        """ returns trailing edge upper and lower x,y of point coordinate data """
        return self._x[0], self._y[0], self._x[-1], self._y[-1], 
    
    @property
    def nPanels_upper (self): 
        """ returns number of panels upper side """
        return self.le_i

    @property
    def nPanels_lower (self): 
        """ returns number of panels lower side """
        return len (self._x) - self.le_i - 1
    
    @property
    def minPanelAngle (self): 
        """ returns the max angle between two panels - something between 160-180° """

        return np.min(panel_angles(self.x,self.y))        

    @property
    def maxThickness (self): 
        """ returns max thickness in %"""
        tx, tmax = self.thickness.maximum() 
        return tmax * 100

    @property
    def maxThicknessX (self): 
        """ returns max thickness x-Position in %"""
        tx, tmax = self.thickness.maximum() 
        return tx * 100

    @property
    def maxCamber (self): 
        """ returns max camber in %"""
        cx, cmax = self.camber.maximum() 
        return cmax * 100

    @property
    def maxCamberX (self): 
        """ returns max camber x-Position in %"""
        cx, cmax = self.camber.maximum() 
        return cx * 100

    @property
    def teGapPercent (self): 
        """ returns trailing edge gap in %"""
        return  (self.y[0] - self.y[-1]) * 100


    @property
    def upper(self) -> 'LineOfAirfoil': 
        """returns the upper surface as a line object - where x 0..1"""
        if self.isLoaded:
            if self._upper is None: 
                self._splitUpperLower ()
            return self._upper
        else: 
            return None
            
    @property
    def lower(self) -> 'LineOfAirfoil': 
        """returns the lower surface as a line object - where x 0..1"""
        if self.isLoaded:
            if self._lower is None: 
                self._splitUpperLower ()
            return self._lower
        else: 
            return None

    @property
    def camber(self) -> 'LineOfAirfoil': 
        """returns the camber line object - where x 0..1  with cosinus distribution"""
        if self.isLoaded:
            if self._camber is None: 
                self._camber = LineOfAirfoil (self.upper.x, (self.upper.y + self.lower.y_interpol(self.upper.x))/2, 
                                              cosinus=False, name='Camber')
            return self._camber
        else: 
            raise ValueError ("Airfoil '%s' not loaded" % self.name)

    @property
    def thickness(self) -> 'LineOfAirfoil': 
        """returns the thickness distribution line object - where x 0..1 with cosinus distribution"""
        if self.isLoaded:
            if self._thickness is None: 
                self._thickness = LineOfAirfoil (self.upper.x, (self.upper.y - self.lower.y_interpol(self.upper.x)), 
                                                 cosinus=True, name='Thickness')
            return self._thickness
        else: 
            raise ValueError ("Airfoil '%s' not loaded" % self.name)

    #-----------------------------------------------------------

    def set_name (self, newName):
        """
        Set der name of the airfoil 
        Note: 
            This will not rename an existing airfoil (file). Use rename instead...
        """

        self.name = newName


    def set_pathFileName (self,fullPath):
        """
        Set der fullpaths of airfoils location and file \n
        ! This will not move or copy the airfoil physically - use clone instead

        Args:
            :newName: String like '..\myAirfoils\JX-GT-15.dat'
        """

        if (os.path.isfile(fullPath)):
            self.pathFileName = fullPath
        else:
            ErrorMsg ("Airfoil \'%s\' does not exist. Couldn\'t be set" % fullPath)

    @property
    def fileName (self):
        """
        Get filename of airfoil 

        Returns: 
            String like 'JX-GT-15.dat'
        """
        if not self.pathFileName is None: 
            return os.path.basename(self.pathFileName) 
        else:
            return None

        

    def load (self, fromPath = None):
        """
        Loads airfoil coordinates from file. 
        pathFileName must be set before or fromPath must be defined.
        Load doesn't change self pathFileName
        """    

        if fromPath and os.path.isfile (fromPath):
            sourcePathFile = fromPath
        elif self.isExisting and not self.isLoaded: 
            sourcePathFile = os.path.join(self.workingDir, self.pathFileName)
        else:
            sourcePathFile = None 

        if sourcePathFile:
            f = open(sourcePathFile, 'r')
            file_lines = f.readlines()
            f.close()
            self._loadLines(file_lines)


    def _loadLines (self, file_lines):
        # read the lines of the airfoil file into self x,y

        x = []
        y = []
        for i, line in enumerate(file_lines):
            if (i > 0): 
                splitline = line.strip().split(" ",1)
                if len(splitline) == 1:                     # couldn't split line - try tab as separator
                    splitline = line.strip().split("\t",1)
                if len(splitline) >= 2:                     
                    x.append (float(splitline[0].strip()))
                    y.append (float(splitline[1].strip()))
            else: 
                self.name = line.strip()
        self._x = np.asarray (x)
        self._y = np.asarray (y)


    def saveAs (self, dir = None, destName = None):
        """
        save self to to destPath and destName and set new values to self
        if both destPath and name are not set, it's just a save to current directory
        """        
        newPathFileName = self.copyAs (dir, destName)
        self.pathFileName =  newPathFileName
        if destName: 
            self.name = destName


    def copyAs (self, dir = None, destName = None):
        """
        Write a copy of self to destPath and destName (the airfoil can be renamed).
        Self remains with its current values 
        return: 
            newPathFileName from dir and destName 
        """        

        if not destName:
            if self.isStrakAirfoil:
                destName = self.sourceName              # strak: take the long name of the two airfoils
            else:
                destName = self.name

        if dir and not os.path.isdir (dir):
            os.mkdir(dir)
            newPathFileName = os.path.join (dir, destName) + '.dat'
        else: 
            newPathFileName = destName + '.dat'

        with open(newPathFileName, 'w+') as file:
            file.write("%s\n" % destName)
            for i in range (len(self.x)):
                file.write("%.7f %.7f\n" %(self.x[i], self.y[i]))
            file.close()

        return newPathFileName
    

    def with_TEGap (self, newGap, xBlend = 0.8):
        """ returns self x,y coordinates with a new te gap.
         The procedere is based on xfoil allowing to define a blending distance from le.

        Arguments: 
            newGap:   in y-coordinates - typically 0.01 or so 
            xblend:   the blending distance from trailing edge 0..1 - Default 0.8
        Returns: 
            x,y:      np coordinate arrays with new Te 
        """

        # currently le must be at 0,0 - te must be at 1,gap/2 (normalized airfoil) 
        if not self.isNormalized: 
            ErrorMsg ("Airfoil '%s' not normalized. Te gap can't be set." % self.name)
            return self.x,self.y
        
        x = np.copy (self.x) 
        y = np.copy (self.y) 
        xBlend = min( max( xBlend , 0.0 ) , 1.0 )

        gap = y[0] - y[-1]
        dgap = newGap - gap 
        ile = self.le_i

        # go over each point, changing the y-thickness appropriately
        for i in range(len(x)):
            # thickness factor tails off exponentially away from trailing edge
            if (xBlend == 0.0): 
                tfac = 0.0
                if (i == 0 or i == (len(x)-1)):
                    tfac = 1.0
            else:
                arg = min ((1.0 - x[i]) * (1.0/xBlend -1.0), 15.0)
                tfac = np.exp(-arg)

            if i <= ile: 
                y[i] = y[i] + 0.5 * dgap * x[i] * tfac # * gap 
            else:
                y[i] = y[i] - 0.5 * dgap * x[i] * tfac # * gap   
        return x,y 


    def plot(self, x=None, y=None):
        """
        Plot the airfoil for testing 
        Alternative coordinates can be supplied 
        """
        import matplotlib.pyplot as plt

        if x is None: x = self.x
        if y is None: y = self.y

        if (x is None or len(x) == 0): 
            ErrorMsg ("No coordinates to plot")
            return 

        fig = plt.figure()
        plt.style.use('seaborn-v0_8-ticks')
        fig.set_figwidth (fig.get_figwidth()  * 2 )     # enlarge window because of 4 plots
        plt.subplots_adjust(left=0.10, bottom=0.10, right=0.95, top=0.90, wspace=None, hspace=None)

        ax = fig.add_subplot(1, 1, 1)
        ax.set_xlim([0.0, 1.0])
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.axis('equal')
        ax.set_title (self.name)
        ax.grid()

        ax.plot(x, y, '-', marker='o', lw=1, fillstyle='none', markersize=4)

        plt.show()    

    def _splitUpperLower (self):
        """ split self._x,y into upper and lower coordinates """

        if not self.isLoaded:
            raise ValueError ("Airfoil '" + self.name + "' isn't loaded. Cannot split.")
        
        iLe = self.le_i

        # upper - extract coordinates - reverse it - now running from 0..1
        self._upper = LineOfAirfoil(np.flip (self._x [0: iLe + 1]), np.flip (self._y [0: iLe + 1]), name='upper')
        # lower - extract coordinates 
        self._lower = LineOfAirfoil(self._x[iLe:], self._y[iLe:], name='lower')




class Airfoil_Straked (Airfoil):
    """ Airfoil which is straked (blended) from it's neighbours"""

    isStrakAirfoil = True

    def __init__ (self):
        super().__init__()

        self.name = "<strak>" 
        self.sourceName = None          # the long name out of the two belended airfoils


    def _save (self, airfoilDict):
        """ stores the variables into the dataDict - returns the filled dict"""
        toDict (airfoilDict, "name",  self.name) 
        return airfoilDict


    def do_strak (self, airfoil1 : Airfoil, airfoil2 : Airfoil, blendBy):
        """ straks (blends) self out of two airfoils to the left and right
        depending on the blendBy factor"""
    
        if blendBy <= 0.5:                      # the closer airfoil provides x-coordinates
            x_ref_upper = airfoil1.upper.x
            x_ref_lower = airfoil1.lower.x
        else:
            x_ref_upper = airfoil2.upper.x
            x_ref_lower = airfoil2.lower.x

        x_upper = x_ref_upper
        y_upper = (1 - blendBy) * airfoil1.upper.y + \
                             blendBy  * airfoil2.upper.y_interpol(x_ref_upper)

        x_lower = x_ref_lower
        y_lower = (1 - blendBy) * airfoil1.lower.y + \
                             blendBy  * airfoil2.lower.y_interpol(x_ref_lower)
        
        self._x = np.concatenate ((np.flip(x_upper), x_lower[1:]))
        self._y = np.concatenate ((np.flip(y_upper), y_lower[1:]))

        self._upper = LineOfAirfoil(x_upper, y_upper, name='upper')
        self._lower = LineOfAirfoil(x_lower, y_lower, name='lower')

        self.sourceName = airfoil1.name + ("_with_%.2f_" % blendBy) + airfoil2.name


# Main program for testing -----------------------------------


if __name__ == "__main__":

    # ---- Test -----
    pass
    # from airfoil_examples import Root_Example
    # import matplotlib.pyplot as plt

    # myAirfoil = Root_Example()
    # print ("New airfoil created: ", myAirfoil)
    # myAirfoil.load()

    # fig = plt.figure()
    # plt.style.use('seaborn-v0_8-ticks')
    # fig.set_figwidth (fig.get_figwidth()  * 2 )     # enlarge window because of 4 plots

    # ax = fig.add_subplot(1, 1, 1)
    # ax.axis('equal')
    # ax.set_title (myAirfoil.name)
    # ax.grid()

    # gap = 0.04

    # for gap in np.linspace (0.0, 0.08, 3):
    #     for xBlend in np.linspace (0.1, 1, 4):
    #         x, y = myAirfoil.with_TEGap (gap,xBlend)
    #         ax.plot(x, y, '-', label="gap=%.2f xBlend=%.2f" % (gap, xBlend))

    #     # myAirfoil.plot(x=x, y=y)
    # ax.legend()
    # plt.subplots_adjust(left=0.10, bottom=0.10, right=0.95, top=0.90, wspace=None, hspace=None)
    # plt.show()    
