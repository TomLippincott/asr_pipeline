import System.Process (readProcessWithExitCode)
import GHC.IO.Handle (hPutStr, hGetContents, hSetBinaryMode)

data Job = Job {name :: String,
                dependencies :: [Dependency],
                resources :: [Resource],
                commands :: [Command]
               }

newtype Dependency = Dependency Int
newtype Resource = Resource String
newtype Command = Command String

main = do
  (exit, stdout, stderr) <- readProcessWithExitCode "/bin/ls" [] ""
  print exit
  print stderr
  print stdout