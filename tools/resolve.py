import os
import sys


def parse_conflict_file(filepath):
    leftfile = path + '.left'
    rightfile = path + '.right'

    lineflag = 3 #bitwise, 1: (0001)local, 2: (0010)remote, 3: (0011)both
    with open(path, 'r') as fp:
        try:
            lfp = open(leftfile, 'wb')
            rfp = open(rightfile, 'wb')

            for no, line in enumerate(fp):
                if line[0: 8] == '<<<<<<< ':
                    lineflag = 1
                    continue
                elif line[0: 7] == '=======':
                    lineflag = 2
                    continue
                elif line[0:8] == '>>>>>>> ':
                    lineflag = 3
                    continue
                else:
                    if lineflag & 1 == 1:
                        lfp.write(line)
                    if lineflag & 2 == 2:
                        rfp.write(line)
        except Exception as e:
            raise
        finally:
            if not lfp is None:
                lfp.close()
            if not rfp is None:
                rfp.close()
    return leftfile, rightfile


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(u'not path specified!')
        print(u'Usage: {0} {{filepath}}'.format(sys.argv[0]))
        sys.exit(1)

    parse_conflict_file(sys.argv[1])