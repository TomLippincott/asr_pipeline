{-# LANGUAGE InstanceSigs #-}

import System.Process (readProcessWithExitCode)
import GHC.IO.Handle (hPutStr, hGetContents, hSetBinaryMode)
import qualified Text.ParserCombinators.Parsec as TPP
import Data.Map (Map)
import Text.ParserCombinators.Parsec (parse, ParseError, GenParser, many, eof, noneOf, oneOf, char, skipMany, skipMany1, space, spaces, newline)

data Job = Job {name :: String,
                dependencies :: [Int],
                resources :: [String],
                array :: Maybe String,
                commands :: [String]
               }

instance Show Job where
  show :: Job -> String
  show x = "#PBS -N " ++ name x


submitJob :: Job -> Either String Int
submitJob j = Right 10
{-
data Host = Host {hostname :: String,
                  state :: String,
                  np :: Int,
                  ntype :: String,
                  status :: Map String String,
                  momServicePort :: String,
                  momManagerPort :: String
                  } deriving (Show)
-}

--newtype Host = Host [String] deriving (Show)

data Host = Host {hostname :: String,
                  fields :: [(String, String)]
                  } deriving (Show)

qnodes :: IO (Either ParseError [Host])
qnodes = do
  (exit, stdout, stderr) <- readProcessWithExitCode "qnodes" [] ""  
  return $ parse nodeInfo "" stdout --[] --map (Host) (lines stdout)
  
nodeInfo :: GenParser Char st [Host]
nodeInfo = do
  nodes <- many node
  eof
  return nodes
  
node :: GenParser Char st Host
node = do
  hostname <- host
  fields <- many field
  emptyLine
  return $ Host {hostname=hostname, fields=fields}

field :: GenParser Char st (String, String)
field = do
  skipMany1 $ char ' '    
  property <- many (noneOf "\n=")
  oneOf "="
  value <- many (noneOf "\n")
  eol
  return (property, value)

host :: GenParser Char st String
host = do
  ret <- many (noneOf "\n")
  eol
  return ret

emptyLine :: GenParser Char st ()
emptyLine = do
  eol
  return ()

eol = char '\n'
  
  
-- nodeInfo = do 
--   result <- many host
--   eof
--   return result

-- host :: GenParser Char st [String]
-- host = 
--     do result <- cells
--        eol                       -- end of line
--        return result





main = do
  (exit, stdout, stderr) <- readProcessWithExitCode "ls" [] ""
  let j = Job "testjob" [] [] Nothing []
      i = submitJob j
  (Right hosts) <- qnodes
  print hosts
  print j
  print i
  print exit
  print stderr
  print stdout